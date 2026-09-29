from django.db.models import Count, Q
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from research.models import Researcher

class ResearcherService:
    """
    Manages author extraction, researcher profiles, and collaboration metrics.
    """

    @classmethod
    def list_researchers(cls, query=None, faculty_name=None, page=1, per_page=16):
        """Returns paginated researchers list with work counts."""
        qs = Researcher.objects.filter(research_count__gt=0).order_by('-research_count', 'name')

        if query:
            qs = qs.filter(
                Q(name__icontains=query) | Q(normalized_name__icontains=query)
            )

        if faculty_name:
            qs = qs.filter(research_items__faculty_name__icontains=faculty_name).distinct()

        paginator = Paginator(qs, per_page)
        try:
            paged = paginator.page(page)
        except PageNotAnInteger:
            paged = paginator.page(1)
        except EmptyPage:
            paged = paginator.page(paginator.num_pages if paginator.num_pages > 0 else 1)

        return {
            'page_obj': paged,
            'total_count': paginator.count,
            'paginator': paginator,
            'query': query or '',
            'faculty_name': faculty_name or '',
        }

    @classmethod
    def get_researcher_profile(cls, researcher_id):
        """Gathers full portfolio and thematic profile for an individual researcher."""
        researcher = Researcher.objects.filter(id=researcher_id).first()
        if not researcher:
            return None

        items = researcher.research_items.select_related('faculty', 'collection').order_by('-publication_year', 'title')
        faculties = researcher.get_faculties()
        active_years = researcher.get_active_years()
        top_keywords = researcher.get_top_keywords()

        return {
            'researcher': researcher,
            'items': items,
            'faculties': faculties,
            'active_years': active_years,
            'top_keywords': top_keywords,
        }
