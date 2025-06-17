from rest_framework import serializers
from .models import Project, Task, Document, Comment, TimelineEvent, Notification
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'confirm_password']

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError("Username already exists.")
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError("Email already exists.")
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data)
        return user
    

class ProjectSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    members = UserSerializer(many=True, read_only=True)
    member_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    tasks_count = serializers.SerializerMethodField()
    documents_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'status', 'created_by', 'members',
                  'member_ids', 'start_date', 'end_date','created_at', 'updated_at',
                  'tasks_count', 'documents_count']
        
    def get_tasks_count(self, obj):
        return obj.tasks.count()
    
    def get_documents_count(self, obj):
        return obj.documents.count()
    
    def create(self, validated_data):
        member_ids = validated_data.pop('member_ids', [])
        project = Project.objects.create(**validated_data)
        if member_ids:
            project.members.set(member_ids)
        return project
    
    def update(self, instance, validated_data):
        member_ids = validated_data.pop('member_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if member_ids is not None:
            instance.members.set(member_ids)
        return instance
    

class TaskSerializer(serializers.ModelSerializer):
    assigned_to = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'project', 'project_name', 
                 'assigned_to', 'status', 'priority', 'due_date', 'created_by',
                 'created_at', 'updated_at', 'comments_count']

    def get_comments_count(self, obj):
        return obj.comments.count()
    

class TaskAssignSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

    def validate_user_id(self, value):
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
        return value
    

class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    file_size = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ['id', 'name', 'file', 'project', 'project_name', 'uploaded_by',
                 'description', 'created_at', 'updated_at', 'file_size']

    def get_file_size(self, obj):
        if obj.file:
            return obj.file.size
        return 0
    

class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'content', 'author', 'project', 'project_name', 
                 'task', 'task_title', 'created_at', 'updated_at']


class TimelineEventSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = TimelineEvent
        fields = ['id', 'project', 'project_name', 'event_type', 'description',
                 'user', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'is_read', 'created_at']
