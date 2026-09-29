from django.contrib import admin
from .models import Faculty, Collection, Researcher, ResearchItem, SyncLog

@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'dspace_collection_uuid', 'item_count', 'created_at')
    search_fields = ('name', 'code')

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'faculty', 'dspace_uuid', 'item_count')
    search_fields = ('name', 'dspace_uuid')
    list_filter = ('faculty',)

@admin.register(Researcher)
class ResearcherAdmin(admin.ModelAdmin):
    list_display = ('name', 'research_count', 'first_seen', 'last_seen')
    search_fields = ('name', 'normalized_name')
    ordering = ('-research_count',)

@admin.register(ResearchItem)
class ResearchItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'faculty_name', 'publication_year', 'item_type', 'handle', 'last_synced')
    search_fields = ('title', 'authors_display', 'abstract', 'handle')
    list_filter = ('faculty_name', 'publication_year', 'item_type')
    readonly_fields = ('dspace_uuid', 'first_seen', 'last_synced', 'updated_at')

@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'started_at', 'records_retrieved', 'records_created', 'records_updated', 'errors_count', 'duration_seconds')
    list_filter = ('status',)
    readonly_fields = ('started_at', 'completed_at', 'records_retrieved', 'records_created', 'records_updated', 'duplicates_skipped', 'errors_count', 'duration_seconds', 'status', 'error_details', 'summary_json')
