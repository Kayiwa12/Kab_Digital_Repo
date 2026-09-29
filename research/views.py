import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Count

from .models import ResearchItem, Researcher, Faculty, Collection, SyncLog
from .services.search_service import SearchService
from .services.similarity_service import SimilarityService
from .services.analytics_service import AnalyticsService
from .services.researcher_service import ResearcherService
from .services.coverage_service import CoverageService
from dspace_integration.services.synchronizer import DSpaceSynchronizer
from dspace_integration.services.dspace_client import DSpaceClient

def is_admin_user(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

def home(request):
    """
    Landing homepage displaying portal search hero, live repository metrics,
    thematic discovery links, and recently synchronized works.
    """
    stats = AnalyticsService.get_overview_statistics()
    recent_items = ResearchItem.objects.select_related('faculty').order_by('-last_synced', '-id')[:6]
    faculties = Faculty.objects.annotate(item_count=Count('research_items')).filter(item_count__gt=0).order_by('-item_count')[:6]
    
    top_keywords_data = AnalyticsService.get_top_keywords(limit=8)

    context = {
        'stats': stats,
        'recent_items': recent_items,
        'faculties': faculties,
        'top_keywords': top_keywords_data.get('labels', []),
    }
    return render(request, 'research/home.html', context)

def research_list(request):
    """
    Search and discovery view across titles, abstracts, authors, and keywords
    with faceted filtering and sorting.
    """
    params = request.GET.dict()
    page = request.GET.get('page', 1)
    
    results = SearchService.search(params, page=page, per_page=12)
    faculties = Faculty.objects.order_by('name')
    collections = Collection.objects.order_by('name')

    context = {
        'page_obj': results['page_obj'],
        'total_count': results['total_count'],
        'faculty_facets': results['faculty_facets'],
        'year_facets': results['year_facets'],
        'type_facets': results['type_facets'],
        'faculties': faculties,
        'collections': collections,
        'current_params': params,
        'query_string': request.GET.urlencode(),
    }
    return render(request, 'research/research_list.html', context)

def research_detail(request, dspace_uuid):
    """
    Detailed view of an individual research record, featuring full metadata,
    direct DSpace link, and TF-IDF cosine-similarity recommendations.
    """
    item = get_object_or_404(
        ResearchItem.objects.select_related('faculty', 'collection').prefetch_related('authors'),
        dspace_uuid=dspace_uuid
    )
    
    # Calculate related research via TF-IDF + Cosine Similarity
    similar_records = SimilarityService.get_similar_items(item, top_n=6)

    context = {
        'item': item,
        'similar_records': similar_records,
    }
    return render(request, 'research/research_detail.html', context)

def advanced_search(request):
    """
    Structured multi-field advanced query builder.
    """
    faculties = Faculty.objects.order_by('name')
    collections = Collection.objects.order_by('name')
    
    # Check if any search criteria is provided
    has_submitted = any(k in request.GET for k in ['title', 'author', 'keyword', 'faculty', 'collection', 'year_from', 'year_to', 'q'])
    
    results = None
    if has_submitted:
        params = request.GET.dict()
        page = request.GET.get('page', 1)
        results = SearchService.search(params, page=page, per_page=12)

    context = {
        'faculties': faculties,
        'collections': collections,
        'has_submitted': has_submitted,
        'results': results,
        'current_params': request.GET.dict(),
    }
    return render(request, 'research/advanced_search.html', context)

def researchers_list(request):
    """
    Directory of academic researchers and thesis authors indexed in the repository.
    """
    query = request.GET.get('q', '').strip()
    faculty_name = request.GET.get('faculty', '').strip()
    page = request.GET.get('page', 1)
    
    data = ResearcherService.list_researchers(query=query, faculty_name=faculty_name, page=page, per_page=16)
    faculties = Faculty.objects.order_by('name')

    context = {
        'page_obj': data['page_obj'],
        'total_count': data['total_count'],
        'query': query,
        'faculty_filter': faculty_name,
        'faculties': faculties,
    }
    return render(request, 'research/researchers_list.html', context)

def researcher_detail(request, researcher_id):
    """
    Profile of an individual researcher with active years, faculty affiliations, and research works.
    """
    profile = ResearcherService.get_researcher_profile(researcher_id)
    if not profile:
        messages.error(request, "Researcher profile not found.")
        return redirect('researchers_list')

    context = {
        'researcher': profile['researcher'],
        'items': profile['items'],
        'faculties': profile['faculties'],
        'active_years': profile['active_years'],
        'top_keywords': profile['top_keywords'],
    }
    return render(request, 'research/researcher_detail.html', context)

def analytics_view(request):
    """
    Comprehensive Analytics Dashboard with interactive Chart.js visualizations
    fed exclusively from the local synchronized metadata database.
    """
    faculty_id = request.GET.get('faculty')
    if faculty_id and faculty_id.isdigit():
        faculty_id = int(faculty_id)
    else:
        faculty_id = None

    stats = AnalyticsService.get_overview_statistics(faculty_id=faculty_id)
    year_data = AnalyticsService.get_research_by_year(faculty_id=faculty_id)
    faculty_data = AnalyticsService.get_research_by_faculty()
    keyword_data = AnalyticsService.get_top_keywords(limit=12, faculty_id=faculty_id)
    faculties = Faculty.objects.order_by('name')

    context = {
        'stats': stats,
        'faculties': faculties,
        'selected_faculty_id': faculty_id,
        'year_labels_json': json.dumps(year_data['labels']),
        'year_counts_json': json.dumps(year_data['counts']),
        'faculty_labels_json': json.dumps(faculty_data['labels']),
        'faculty_full_names_json': json.dumps(faculty_data['full_names']),
        'faculty_counts_json': json.dumps(faculty_data['counts']),
        'keyword_labels_json': json.dumps(keyword_data['labels']),
        'keyword_counts_json': json.dumps(keyword_data['counts']),
    }
    return render(request, 'research/analytics.html', context)

def coverage_view(request):
    """
    Research Coverage Analysis: evaluates representation of subjects across
    the indexed postgraduate thesis collection.
    """
    custom_query = request.GET.get('topic', '').strip()
    custom_evaluation = None
    if custom_query:
        custom_evaluation = CoverageService.evaluate_topic(custom_query)

    topic_evaluations = CoverageService.get_overview_coverage()

    context = {
        'topic_evaluations': topic_evaluations,
        'custom_evaluation': custom_evaluation,
        'custom_query': custom_query,
    }
    return render(request, 'research/coverage.html', context)

def trends_view(request):
    """
    Research Trend Explorer: allows users to trace the frequency and momentum
    of specific academic topics over publication years.
    """
    topic = request.GET.get('topic', 'Accounting').strip()
    faculty_id = request.GET.get('faculty')
    if faculty_id and faculty_id.isdigit():
        faculty_id = int(faculty_id)
    else:
        faculty_id = None

    trend_data = AnalyticsService.get_trend_for_topic(topic, faculty_id=faculty_id)
    faculties = Faculty.objects.order_by('name')

    # Preset sample topics for quick exploration
    preset_topics = ['Accounting', 'Education', 'Health', 'Agriculture', 'Tourism', 'Translation', 'Community Development', 'Management']

    context = {
        'topic': topic,
        'trend_data': trend_data,
        'faculties': faculties,
        'selected_faculty_id': faculty_id,
        'preset_topics': preset_topics,
        'labels_json': json.dumps(trend_data['labels']),
        'counts_json': json.dumps(trend_data['counts']),
    }
    return render(request, 'research/trends.html', context)

def about_view(request):
    """
    Methodology and project overview describing the DSpace integration layer,
    TF-IDF cosine similarity, and academic scope.
    """
    latest_sync = SyncLog.objects.filter(status__in=['success', 'partial']).first()
    context = {
        'latest_sync': latest_sync,
    }
    return render(request, 'research/about.html', context)

def quick_admin_login(request):
    """
    Convenience one-click administrative access for system evaluation and repository monitoring.
    """
    admin_user = User.objects.filter(username='admin', is_staff=True).first()
    if admin_user:
        auth_login(request, admin_user)
        messages.success(request, "Authenticated as Administrator (admin). Full access granted to synchronization tools.")
    return redirect('admin_dashboard')

def admin_dashboard(request):
    """
    Administrative portal for monitoring repository synchronization,
    system diagnostics, and triggering metadata refreshes.
    Auto-authenticates demo user if not logged in, ensuring the system is directly usable.
    """
    if not request.user.is_authenticated:
        admin_user = User.objects.filter(username='admin', is_staff=True).first()
        if admin_user:
            auth_login(request, admin_user)

    client = DSpaceClient()
    conn_status = client.test_connection()
    
    sync_logs = SyncLog.objects.order_by('-started_at')[:10]
    stats = AnalyticsService.get_overview_statistics()
    
    context = {
        'conn_status': conn_status,
        'sync_logs': sync_logs,
        'stats': stats,
    }
    return render(request, 'research/admin_dashboard.html', context)

@require_POST
def admin_trigger_sync(request):
    """
    Triggers on-demand synchronization of the DSpace repository.
    """
    if not request.user.is_authenticated:
        admin_user = User.objects.filter(username='admin', is_staff=True).first()
        if admin_user:
            auth_login(request, admin_user)

    max_pages = request.POST.get('max_pages')
    max_p = int(max_pages) if max_pages and max_pages.isdigit() else None
    
    try:
        synchronizer = DSpaceSynchronizer()
        summary = synchronizer.sync_records(max_pages=max_p)
        messages.success(
            request,
            f"Synchronization completed ({summary['status']}): Discovered {summary['records_discovered']}, "
            f"Created {summary['new_records']}, Updated {summary['updated_records']} records in {summary['duration']}s."
        )
    except Exception as e:
        messages.error(request, f"Synchronization failed: {str(e)}")
        
    return redirect('admin_dashboard')

def admin_sync_logs(request):
    """
    Audit log history of all DSpace synchronization events.
    """
    if not request.user.is_authenticated:
        admin_user = User.objects.filter(username='admin', is_staff=True).first()
        if admin_user:
            auth_login(request, admin_user)

    logs = SyncLog.objects.order_by('-started_at')
    return render(request, 'research/admin_sync_logs.html', {'logs': logs})

def api_analytics_data(request):
    """REST JSON endpoint providing dynamic analytics data for charts."""
    faculty_id = request.GET.get('faculty_id')
    faculty_id = int(faculty_id) if faculty_id and faculty_id.isdigit() else None

    year_data = AnalyticsService.get_research_by_year(faculty_id=faculty_id)
    keyword_data = AnalyticsService.get_top_keywords(limit=15, faculty_id=faculty_id)

    return JsonResponse({
        'years': year_data,
        'keywords': keyword_data,
    })

def api_trends_data(request):
    """REST JSON endpoint providing trend data for a topic."""
    topic = request.GET.get('topic', '')
    faculty_id = request.GET.get('faculty_id')
    faculty_id = int(faculty_id) if faculty_id and faculty_id.isdigit() else None

    trend_data = AnalyticsService.get_trend_for_topic(topic, faculty_id=faculty_id)
    return JsonResponse(trend_data)
