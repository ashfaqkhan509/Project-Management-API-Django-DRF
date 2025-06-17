from django.contrib import admin
from .models import Project, Task, Document, Comment, TimelineEvent, Notification

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    ordering = ('-created_at',)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'assigned_to', 'status', 'created_at', 'updated_at')
    search_fields = ('title', 'description')
    list_filter = ('status', 'project')
    ordering = ('-created_at',)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'uploaded_by', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('project',)
    ordering = ('-created_at',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'task', 'created_at', 'updated_at')
    search_fields = ('content',)
    list_filter = ('task',)
    ordering = ('-created_at',)


@admin.register(TimelineEvent)
class TimelineEventAdmin(admin.ModelAdmin):
    list_display = ('project', 'event_type', 'user', 'created_at')
    search_fields = ('description',)
    list_filter = ('event_type', 'project')
    ordering = ('-created_at',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    search_fields = ('message',)
    list_filter = ('is_read', 'user')
    ordering = ('-created_at',)