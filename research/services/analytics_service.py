import re
from collections import Counter
from django.db.models import Count, Min, Max
from research.models import ResearchItem, Researcher, Faculty, Collection

STOP_WORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'as', 'at',
    'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'can', 'did', 'do',
    'does', 'doing', 'down', 'during', 'each', 'few', 'for', 'from', 'further', 'had', 'has', 'have', 'having',
    'he', 'her', 'here', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it',
    'its', 'itself', 'just', 'me', 'more', 'most', 'my', 'myself', 'no', 'nor', 'not', 'now', 'of', 'off', 'on',
    'once', 'only', 'or', 'other', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 's', 'same', 'she', 'should',
    'so', 'some', 'such', 't', 'than', 'that', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there',
    'these', 'they', 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'we', 'were',
    'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why', 'will', 'with', 'study', 'case', 'uganda',
    'kabale', 'district', 'municipality', 'role', 'impact', 'assessment', 'effect', 'effects', 'factors', 'influence',
    'performance', 'investigation', 'evaluation', 'analysis'
}

class AnalyticsService:
    """
    Computes real-time empirical aggregates, trends, and distributions from synchronized repository records.
    """

    @classmethod
    def get_overview_statistics(cls, faculty_id=None, year_from=None, year_to=None):
        """Computes summary KPI indicators."""
        qs = ResearchItem.objects.all()
        if faculty_id:
            qs = qs.filter(faculty_id=faculty_id)
        if year_from:
            qs = qs.filter(publication_year__gte=year_from)
        if year_to:
            qs = qs.filter(publication_year__lte=year_to)

        total_records = qs.count()
        total_researchers = Researcher.objects.count()
        total_faculties = Faculty.objects.count()
        total_collections = Collection.objects.count()

        year_bounds = qs.exclude(publication_year__isnull=True).aggregate(
            min_year=Min('publication_year'),
            max_year=Max('publication_year')
        )

        return {
            'total_records': total_records,
            'total_researchers': total_researchers,
            'total_faculties': total_faculties,
            'total_collections': total_collections,
            'min_year': year_bounds['min_year'] or 'N/A',
            'max_year': year_bounds['max_year'] or 'N/A',
        }

    @classmethod
    def get_research_by_year(cls, faculty_id=None):
        """Returns research record counts grouped by publication year."""
        qs = ResearchItem.objects.exclude(publication_year__isnull=True)
        if faculty_id:
            qs = qs.filter(faculty_id=faculty_id)

        data = qs.values('publication_year').annotate(count=Count('id')).order_by('publication_year')
        
        labels = [str(d['publication_year']) for d in data]
        counts = [d['count'] for d in data]
        return {
            'labels': labels,
            'counts': counts,
        }

    @classmethod
    def get_research_by_faculty(cls, min_year=None, max_year=None):
        """Returns research count grouped by academic faculty."""
        qs = ResearchItem.objects.exclude(faculty_name='')
        if min_year:
            qs = qs.filter(publication_year__gte=min_year)
        if max_year:
            qs = qs.filter(publication_year__lte=max_year)

        data = qs.values('faculty_name').annotate(count=Count('id')).order_by('-count')
        
        # Abbreviate long names for chart labels
        labels = []
        full_names = []
        counts = []
        for d in data:
            name = d['faculty_name']
            full_names.append(name)
            if '(' in name and ')' in name:
                abbr = name[name.rfind('(')+1:name.rfind(')')].strip()
                labels.append(abbr if abbr else name[:25])
            else:
                labels.append(name[:25] + ('...' if len(name) > 25 else ''))
            counts.append(d['count'])

        return {
            'labels': labels,
            'full_names': full_names,
            'counts': counts,
        }

    @classmethod
    def get_top_keywords(cls, limit=15, faculty_id=None):
        """Aggregates and normalizes subject and keyword metadata."""
        qs = ResearchItem.objects.all()
        if faculty_id:
            qs = qs.filter(faculty_id=faculty_id)

        counter = Counter()
        for item in qs.only('subjects', 'keywords'):
            raw_terms = (item.subjects or []) + (item.keywords or [])
            for term in raw_terms:
                cleaned = term.strip().lower()
                # Remove punctuation
                cleaned = re.sub(r'^[^\w]+|[^\w]+$', '', cleaned)
                if cleaned and len(cleaned) > 2 and cleaned not in STOP_WORDS:
                    counter[cleaned.title()] += 1

        top_pairs = counter.most_common(limit)
        return {
            'labels': [k for k, _ in top_pairs],
            'counts': [c for _, c in top_pairs],
        }

    @classmethod
    def get_trend_for_topic(cls, topic, faculty_id=None):
        """
        Calculates longitudinal trend for a specific topic / keyword across publication years.
        Returns yearly breakdown.
        """
        clean_topic = topic.strip()
        if not clean_topic:
            return {'labels': [], 'counts': [], 'total_matches': 0}

        qs = ResearchItem.objects.exclude(publication_year__isnull=True).filter(
            search_vector_text__icontains=clean_topic
        )
        if faculty_id:
            qs = qs.filter(faculty_id=faculty_id)

        total_matches = qs.count()
        yearly = qs.values('publication_year').annotate(count=Count('id')).order_by('publication_year')

        # Fill potential year gaps between min and max
        if yearly:
            all_years = list(range(yearly[0]['publication_year'], yearly[len(yearly)-1]['publication_year'] + 1))
            year_map = {d['publication_year']: d['count'] for d in yearly}
            labels = [str(y) for y in all_years]
            counts = [year_map.get(y, 0) for y in all_years]
        else:
            labels = []
            counts = []

        return {
            'topic': clean_topic,
            'labels': labels,
            'counts': counts,
            'total_matches': total_matches,
        }
