from .models import ResearchItem, Researcher, Faculty, Collection, SyncLog

def repo_context(request):
    """
    Provides repository context variables to all templates.
    """
    total_items = ResearchItem.objects.count()
    total_researchers = Researcher.objects.count()
    total_faculties = Faculty.objects.count()
    total_collections = Collection.objects.count()
    latest_sync = SyncLog.objects.filter(status__in=['success', 'partial']).first()
    
    return {
        'STAT_TOTAL_ITEMS': total_items,
        'STAT_TOTAL_RESEARCHERS': total_researchers,
        'STAT_TOTAL_FACULTIES': total_faculties,
        'STAT_TOTAL_COLLECTIONS': total_collections,
        'LATEST_SYNC': latest_sync,
        'UNIVERSITY_NAME': 'Kabale University',
        'REPOSITORY_NAME': 'Kabale University Institutional Digital Repository (IDR)',
        'PLATFORM_TITLE': 'Enhanced Research Discovery & Analytics Platform',
    }
