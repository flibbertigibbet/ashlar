from collections import OrderedDict
from datetime import datetime, timedelta

from django.db import IntegrityError, connection
from django.db.models import Case, When, IntegerField, Value, Count

from rest_framework import viewsets, mixins, status
from rest_framework.decorators import detail_route, list_route
from rest_framework.filters import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework_gis.filters import InBBoxFilter

from ashlar.models import (Boundary,
                           BoundaryPolygon,
                           Record,
                           RecordType,
                           RecordSchema)
from ashlar.serializers import (BoundarySerializer,
                                BoundaryPolygonSerializer,
                                BoundaryPolygonNoGeomSerializer,
                                RecordSerializer,
                                RecordTypeSerializer,
                                RecordSchemaSerializer)
from ashlar.filters import (BoundaryFilter,
                            BoundaryPolygonFilter,
                            JsonBFilterBackend,
                            RecordFilter,
                            RecordTypeFilter,
                            DateRangeFilterBackend)

from ashlar.pagination import OptionalLimitOffsetPagination


class BoundaryPolygonViewSet(viewsets.ModelViewSet):

    queryset = BoundaryPolygon.objects.all()
    serializer_class = BoundaryPolygonSerializer
    filter_class = BoundaryPolygonFilter
    pagination_class = OptionalLimitOffsetPagination
    bbox_filter_field = 'geom'
    jsonb_filter_field = 'data'
    filter_backends = (InBBoxFilter, JsonBFilterBackend, DjangoFilterBackend)

    def get_serializer_class(self):
        if 'nogeom' in self.request.query_params and self.request.query_params['nogeom']:
            return BoundaryPolygonNoGeomSerializer
        return BoundaryPolygonSerializer


class RecordViewSet(viewsets.ModelViewSet):

    queryset = Record.objects.all()
    serializer_class = RecordSerializer
    filter_class = RecordFilter
    bbox_filter_field = 'geom'
    jsonb_filter_field = 'data'
    filter_backends = (InBBoxFilter, JsonBFilterBackend,
                       DjangoFilterBackend, DateRangeFilterBackend)

    def list(self, request, *args, **kwargs):
        # respond to `query` param with the SQL for the query, instead of the query results
        if 'query' in request.GET:
            qryset = self.get_queryset()
            # apply the filters
            for backend in list(self.filter_backends):
                qryset = backend().filter_queryset(request, qryset, self)

            cursor = connection.cursor().cursor
            sql, params = qryset.query.sql_with_params()
            # get properly escaped string representation of the query
            qrystr = cursor.mogrify(sql, params)
            cursor.close()

            return Response({'query': qrystr})
        else:
            return super(RecordViewSet, self).list(self, request, *args, **kwargs)

    @list_route(methods=['get'])
    def toddow(self, request):
        """ Return aggregations which nicely format the counts for time of day and day of week
        """
        qryset = self.get_queryset()
        for backend in list(self.filter_backends):
            qryset = backend().filter_queryset(request, qryset, self)

        # Build SQL `case` statement to annotate with the day of week
        dow_case = Case(*[When(occurred_from__week_day=x, then=Value(x))
                          for x in xrange(1, 8)], output_field=IntegerField())
        # Build SQL `case` statement to annotate with the time of day
        tod_case = Case(*[When(occurred_from__hour=x, then=Value(x))
                          for x in xrange(24)], output_field=IntegerField())
        annotated_recs = qryset.annotate(dow=dow_case).annotate(tod=tod_case)

        # Voodoo to perform aggregations over `tod` and `dow` combinations
        counted = (annotated_recs.values('tod', 'dow')
                   .order_by('tod', 'dow')
                   .annotate(count=Count('tod')))

        return Response(counted)


class RecordTypeViewSet(viewsets.ModelViewSet):
    queryset = RecordType.objects.all()
    serializer_class = RecordTypeSerializer
    filter_class = RecordTypeFilter
    pagination_class = OptionalLimitOffsetPagination
    ordering = ('plural_label',)

    @detail_route(methods=['get'])
    def recent_counts(self, request, pk=None):
        """ Return the recent record counts for a given a record type
        where recent = 30, 90, 365 days
        """
        record_type = RecordType.objects.get(pk=pk)
        now = datetime.now()
        durations = {
            'month': 30,
            'quarter': 90,
            'year': 365
        }

        counts = {
            'month': 0,
            'quarter': 0,
            'year': 0
        }

        for schema in record_type.schemas.all():
            for label, days in durations.items():
                earliest = now - timedelta(days=days)
                count = (schema.record_set
                         .filter(occurred_from__lte=now, occurred_from__gte=earliest).count())
                counts[label] += count

        # Construct JSON representation of `counts` for the response
        return Response(counts)


class SchemaViewSet(viewsets.GenericViewSet,
                    mixins.ListModelMixin,
                    mixins.CreateModelMixin,
                    mixins.RetrieveModelMixin):  # Schemas are immutable
    """Base ViewSet for viewsets displaying subclasses of SchemaModel"""
    pagination_class = OptionalLimitOffsetPagination


class RecordSchemaViewSet(SchemaViewSet):
    queryset = RecordSchema.objects.all()
    serializer_class = RecordSchemaSerializer
    jsonb_filter_field = 'schema'
    filter_backends = (JsonBFilterBackend, DjangoFilterBackend)

    # N.B. The DRF documentation is misleading; if you include named parameters as
    # shown in the documentation, this will cause list and detail endpoints to
    # throw Serializer errors.
    def get_serializer(self, *args, **kwargs):
        """Override data passed to serializer with incremented version if necessary"""
        if self.action == 'create' and 'data' in kwargs and 'record_type' in kwargs['data']:
            try:
                version = RecordSchema.objects.get(record_type=kwargs['data']['record_type'],
                                                   next_version=None).version + 1
            except RecordSchema.DoesNotExist:
                version = 1
            kwargs['data']['version'] = version
        return super(RecordSchemaViewSet, self).get_serializer(*args, **kwargs)


class BoundaryViewSet(viewsets.ModelViewSet):

    queryset = Boundary.objects.all()
    serializer_class = BoundarySerializer
    filter_class = BoundaryFilter
    pagination_class = OptionalLimitOffsetPagination
    ordering = ('display_field',)

    def create(self, request, *args, **kwargs):
        """Overwritten to allow use of semantically important/appropriate status codes for
        informing users about the type of error they've encountered
        """
        try:
            return super(BoundaryViewSet, self).create(request, *args, **kwargs)
        except IntegrityError:
            return Response({'error': 'uniqueness constraint violation'}, status.HTTP_409_CONFLICT)

    @detail_route(methods=['get'])
    def geojson(self, request, pk=None):
        """ Print boundary polygons as geojson FeatureCollection

        Pretty non-performant, and geojson responses get large quickly.
        TODO: Consider other solutions

        """
        boundary = self.get_object()
        polygons = boundary.polygons.values()
        serializer = BoundaryPolygonSerializer()
        features = [serializer.to_representation(polygon) for polygon in polygons]
        data = OrderedDict((
            ('type', 'FeatureCollection'),
            ('features', features)
        ))
        return Response(data)
