from django.db.models import Count, Min, Max
from research.models import ResearchItem, Faculty

DEFAULT_TOPICS = [
    'Cybersecurity',
    'Machine Learning',
    'Climate Change',
    'Maternal Health',
    'Renewable Energy',
    'Food Security',
    'Microfinance',
    'Curriculum Development',
    'Environmental Law',
    'Ecotourism',
    'Indigenous Languages',
    'Public Health Surveillance',
    'Telemedicine',
    'Soil Conservation',
    'E-Commerce',
    'Tax Compliance',
    'Waste Management',
    'Mental Health'
]

class CoverageService:
    """
    Computes empirical coverage metrics for topics within the indexed institutional repository dataset.
    Follows strict academic caveats: analyzes only locally indexed DSpace records, avoids claims of scientific absence.
    """

    @classmethod
    def evaluate_topic(cls, topic_str):
        """
        Calculates repository coverage for a single topic or phrase.
        """
        clean_topic = topic_str.strip()
        total_items = ResearchItem.objects.count()
        if total_items == 0:
            return {
                'topic': clean_topic,
                'count': 0,
                'percentage': 0.0,
                'coverage_label': 'Insufficient Dataset',
                'years': [],
                'faculties': [],
                'status_class': 'secondary',
                'caveat_note': 'The repository database has not yet been synchronized.',
            }

        matches = ResearchItem.objects.filter(search_vector_text__icontains=clean_topic)
        count = matches.count()
        percentage = round((count / total_items) * 100, 2)

        faculties = list(matches.exclude(faculty_name='').values_list('faculty_name', flat=True).distinct())
        years = list(matches.exclude(publication_year__isnull=True).values_list('publication_year', flat=True).distinct())
        years = sorted([y for y in years if y])

        if count >= 15:
            coverage_label = 'Substantial Repository Coverage'
            status_class = 'success'
            description = 'Topic is prominently represented across multiple departments and cohorts in the indexed collection.'
        elif count >= 5:
            coverage_label = 'Moderate Repository Coverage'
            status_class = 'primary'
            description = 'Topic has established presence in several indexed postgraduate studies.'
        elif count > 0:
            coverage_label = 'Low Repository Coverage'
            status_class = 'warning'
            description = 'Based on the research records currently indexed by this platform, this topic has relatively low repository coverage.'
        else:
            coverage_label = 'Underrepresented in Indexed Dataset'
            status_class = 'secondary'
            description = 'Based on the research records currently indexed by this platform, no records directly matching this term were found in the postgraduate collection.'

        return {
            'topic': clean_topic,
            'count': count,
            'total_repository_items': total_items,
            'percentage': percentage,
            'coverage_label': coverage_label,
            'status_class': status_class,
            'description': description,
            'years': years,
            'faculties': faculties,
            'sample_items': list(matches[:3]),
        }

    @classmethod
    def get_overview_coverage(cls, topic_list=None):
        """
        Evaluates a suite of domain topics to provide a comparative landscape of repository representation.
        """
        topics = topic_list or DEFAULT_TOPICS
        evaluations = [cls.evaluate_topic(t) for t in topics]
        # Sort by count descending
        return sorted(evaluations, key=lambda x: x['count'], reverse=True)
