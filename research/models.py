from django.db import models
from django.utils import timezone
import json
import re

class Faculty(models.Model):
    """
    Academic Faculty or Institute at Kabale University.
    """
    name = models.CharField(max_length=300, unique=True)
    code = models.CharField(max_length=50, blank=True, default='')
    dspace_collection_uuid = models.CharField(max_length=64, blank=True, default='', db_index=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Faculties'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def item_count(self):
        return self.research_items.count()


class Collection(models.Model):
    """
    DSpace Collection representing a repository collection.
    """
    dspace_uuid = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=400)
    handle = models.CharField(max_length=100, blank=True, default='')
    faculty = models.ForeignKey(Faculty, null=True, blank=True, on_delete=models.SET_NULL, related_name='collections')
    community_name = models.CharField(max_length=300, default='Postgraduate Masters Theses/Reports')
    item_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Researcher(models.Model):
    """
    Researcher / Author extracted from DSpace metadata records.
    """
    name = models.CharField(max_length=300, db_index=True)
    normalized_name = models.CharField(max_length=300, db_index=True, unique=True)
    research_count = models.IntegerField(default=0)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-research_count', 'name']

    def __str__(self):
        return self.name

    def get_faculties(self):
        """Returns distinct faculties associated with this researcher's works."""
        facs = set()
        for item in self.research_items.select_related('faculty').all():
            if item.faculty:
                facs.add(item.faculty.name)
            elif item.faculty_name:
                facs.add(item.faculty_name)
        return sorted(list(facs))

    def get_active_years(self):
        """Returns sorted list of publication years for researcher."""
        years = self.research_items.filter(publication_year__isnull=False).values_list('publication_year', flat=True).distinct()
        return sorted([y for y in years if y])

    def get_top_keywords(self, limit=8):
        """Returns top keyword occurrences for this researcher."""
        counts = {}
        for item in self.research_items.all():
            for kw in item.keywords:
                kw_clean = kw.strip().title()
                if kw_clean:
                    counts[kw_clean] = counts.get(kw_clean, 0) + 1
        sorted_kw = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [k for k, _ in sorted_kw[:limit]]


class ResearchItem(models.Model):
    """
    Local synchronized research metadata record originating from Kabale University DSpace.
    """
    dspace_uuid = models.CharField(max_length=64, unique=True, db_index=True)
    title = models.TextField(db_index=True)
    abstract = models.TextField(blank=True, default='')
    authors_display = models.TextField(blank=True, default='')
    authors = models.ManyToManyField(Researcher, related_name='research_items', blank=True)
    subjects = models.JSONField(default=list, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    publication_year = models.IntegerField(null=True, blank=True, db_index=True)
    date_issued = models.CharField(max_length=50, blank=True, default='')
    
    faculty = models.ForeignKey(Faculty, null=True, blank=True, on_delete=models.SET_NULL, related_name='research_items')
    faculty_name = models.CharField(max_length=300, blank=True, default='', db_index=True)
    
    collection = models.ForeignKey(Collection, null=True, blank=True, on_delete=models.SET_NULL, related_name='research_items')
    collection_name = models.CharField(max_length=300, blank=True, default='')
    
    community = models.CharField(max_length=300, default='Postgraduate Masters Theses/Reports')
    community_uuid = models.CharField(max_length=64, default='95cbea8b-fdc6-4d8a-9f20-d51ad2814f12')
    
    handle = models.CharField(max_length=100, blank=True, default='', db_index=True)
    dspace_url = models.URLField(max_length=500, blank=True, default='')
    bitstream_url = models.URLField(max_length=500, blank=True, default='')
    item_type = models.CharField(max_length=100, default='Thesis', db_index=True)
    
    metadata_json = models.JSONField(default=dict, blank=True)
    search_vector_text = models.TextField(blank=True, default='')
    
    first_seen = models.DateTimeField(auto_now_add=True)
    last_synced = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-publication_year', 'title']
        indexes = [
            models.Index(fields=['dspace_uuid']),
            models.Index(fields=['publication_year']),
            models.Index(fields=['faculty_name']),
            models.Index(fields=['handle']),
        ]

    def __str__(self):
        return self.title[:100]

    def get_dspace_direct_url(self):
        """Constructs or returns the authoritative public DSpace URL."""
        if self.dspace_url and 'http' in self.dspace_url:
            return self.dspace_url
        if self.handle:
            clean_handle = self.handle.strip()
            if not clean_handle.startswith('http'):
                return f"https://idr.kab.ac.ug/handle/{clean_handle}"
            return clean_handle
        return f"https://backend.kab.ac.ug/server/api/core/items/{self.dspace_uuid}"

    def short_abstract(self, max_length=240):
        if not self.abstract:
            return "No abstract available for this record in the institutional repository."
        if len(self.abstract) <= max_length:
            return self.abstract
        return self.abstract[:max_length].rstrip() + '...'

    def all_keywords(self):
        """Combines subjects and keywords into a unique list."""
        all_kw = []
        seen = set()
        for kw in (self.subjects or []) + (self.keywords or []):
            clean = kw.strip()
            lower = clean.lower()
            if clean and lower not in seen:
                seen.add(lower)
                all_kw.append(clean)
        return all_kw


class SyncLog(models.Model):
    """
    Audit log for DSpace synchronization runs.
    """
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('success', 'Completed Successfully'),
        ('partial', 'Completed with Errors'),
        ('failed', 'Failed'),
    ]

    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    records_retrieved = models.IntegerField(default=0)
    records_created = models.IntegerField(default=0)
    records_updated = models.IntegerField(default=0)
    duplicates_skipped = models.IntegerField(default=0)
    errors_count = models.IntegerField(default=0)
    duration_seconds = models.FloatField(default=0.0)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='in_progress')
    error_details = models.TextField(blank=True, default='')
    summary_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"Sync #{self.id} ({self.status}) at {self.started_at.strftime('%Y-%m-%d %H:%M:%S')}"
