from django.db.models import Q, Count, Case, When, IntegerField
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from research.models import ResearchItem, Faculty, Collection

class SearchService:
    """
    Handles local query execution, multi-criteria filtering, ranking, and faceting.
    """

    @classmethod
    def search(cls, params, page=1, per_page=12):
        """
        Executes search with support for keywords, faculty, date range, and sorting.
        """
        queryset = ResearchItem.objects.select_related('faculty', 'collection').prefetch_related('authors').all()

        q = params.get('q', '').strip()
        title_q = params.get('title', '').strip()
        author_q = params.get('author', '').strip()
        keyword_q = params.get('keyword', '').strip()
        faculty_q = params.get('faculty', '').strip()
        collection_q = params.get('collection', '').strip()
        year_from = params.get('year_from', '').strip()
        year_to = params.get('year_to', '').strip()
        item_type = params.get('item_type', '').strip()
        sort = params.get('sort', 'relevance').strip()

        # General text query
        if q:
            # Match anywhere in title, abstract, authors_display, handle, or search_vector_text
            terms = q.split()
            query_filter = Q()
            for term in terms:
                term_filter = (
                    Q(title__icontains=term) |
                    Q(abstract__icontains=term) |
                    Q(authors_display__icontains=term) |
                    Q(handle__icontains=term) |
                    Q(search_vector_text__icontains=term)
                )
                query_filter &= term_filter
            queryset = queryset.filter(query_filter)

        # Specific field criteria
        if title_q:
            queryset = queryset.filter(title__icontains=title_q)

        if author_q:
            queryset = queryset.filter(
                Q(authors_display__icontains=author_q) |
                Q(authors__name__icontains=author_q)
            ).distinct()

        if keyword_q:
            queryset = queryset.filter(
                Q(search_vector_text__icontains=keyword_q) |
                Q(title__icontains=keyword_q)
            )

        if faculty_q:
            if faculty_q.isdigit():
                queryset = queryset.filter(faculty_id=int(faculty_q))
            else:
                queryset = queryset.filter(Q(faculty_name__icontains=faculty_q) | Q(faculty__name__icontains=faculty_q))

        if collection_q:
            if collection_q.isdigit():
                queryset = queryset.filter(collection_id=int(collection_q))
            else:
                queryset = queryset.filter(collection__name__icontains=collection_q)

        if year_from and year_from.isdigit():
            queryset = queryset.filter(publication_year__gte=int(year_from))

        if year_to and year_to.isdigit():
            queryset = queryset.filter(publication_year__lte=int(year_to))

        if item_type:
            queryset = queryset.filter(item_type__iexact=item_type)

        # Sorting logic
        if sort == 'newest':
            queryset = queryset.order_by('-publication_year', '-id')
        elif sort == 'oldest':
            queryset = queryset.order_by('publication_year', 'id')
        elif sort == 'title':
            queryset = queryset.order_by('title')
        elif sort == 'relevance' and q:
            # Score items higher if query appears directly in title vs abstract
            queryset = queryset.annotate(
                relevance_rank=Case(
                    When(title__icontains=q, then=3),
                    When(authors_display__icontains=q, then=2),
                    When(search_vector_text__icontains=q, then=1),
                    default=0,
                    output_field=IntegerField()
                )
            ).order_by('-relevance_rank', '-publication_year', '-id')
        else:
            queryset = queryset.order_by('-publication_year', '-id')

        # Pagination
        paginator = Paginator(queryset, per_page)
        try:
            paged_results = paginator.page(page)
        except PageNotAnInteger:
            paged_results = paginator.page(1)
        except EmptyPage:
            paged_results = paginator.page(paginator.num_pages if paginator.num_pages > 0 else 1)

        # Calculate facets based on current matching queryset (or overall if no query)
        faculty_facets = queryset.exclude(faculty_name='').values('faculty_name').annotate(count=Count('id')).order_by('-count')[:10]
        year_facets = queryset.exclude(publication_year__isnull=True).values('publication_year').annotate(count=Count('id')).order_by('-publication_year')[:10]
        type_facets = queryset.exclude(item_type='').values('item_type').annotate(count=Count('id')).order_by('-count')[:5]

        return {
            'page_obj': paged_results,
            'total_count': paginator.count,
            'paginator': paginator,
            'faculty_facets': faculty_facets,
            'year_facets': year_facets,
            'type_facets': type_facets,
            'query_params': params,
        }
