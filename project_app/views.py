from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Project, Task, Document, Comment, TimelineEvent, Notification
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.db import models
from .serializers import (
    TaskAssignSerializer, UserSerializer, UserRegisterSerializer, ProjectSerializer, TaskSerializer,
    DocumentSerializer, CommentSerializer, TimelineEventSerializer, NotificationSerializer
)


# Authentication Views
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        response_data = {
            "user": UserSerializer(user).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "message": "User registered successfully."
        }
        return Response(response_data, status=status.HTTP_201_CREATED)
    

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response({"error": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)
    
    user = authenticate(request, username=username, password=password)
    
    if user is None:
        return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
    
    refresh = RefreshToken.for_user(user)
    response_data = {
        "user": UserSerializer(user).data,
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "message": "Login successful."
    }
    return Response(response_data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({"error": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"message": "Logout successful."}, status=status.HTTP_205_RESET_CONTENT)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

# Project Views
class ProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(
            models.Q(created_by=self.request.user) |
            models.Q(members=self.request.user)
        ).distinct()
    
    def perform_create(self, serializer):
        project = serializer.save(created_by=self.request.user)

        # create a timeline event for project creation
        TimelineEvent.objects.create(
            project=project,
            event_type='project_created',
            user=self.request.user,
            description=f"Project '{project.name}' created."
        )


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(
            models.Q(created_by=self.request.user) |
            models.Q(members=self.request.user)
        ).distinct()
    

# Task Views
class TaskListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project_id = self.request.query_params.get('project', None)
        queryset = Task.objects.filter(
            project__in=Project.objects.filter(
                models.Q(created_by=self.request.user) | 
                models.Q(members=self.request.user)
            )
        )

        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset
    
    def perform_create(self, serializer):
        task = serializer.save(created_by=self.request.user)

        # create a timeline event for task creation
        TimelineEvent.objects.create(
            project=task.project,
            event_type='task_created',
            user=self.request.user,
            description=f"Task '{task.title}' created in project '{task.project.name}'."
        )
    

class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(
            project__in=Project.objects.filter(
                models.Q(created_by=self.request.user) | 
                models.Q(members=self.request.user)
            )
        )
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if not (task.project.created_by == request.user or request.user in task.project.members.all()):
        return Response({"error": "You do not have permission to assign this task."}, status=status.HTTP_403_FORBIDDEN)
    
    serializer = TaskAssignSerializer(data=request.data)
    if serializer.is_valid():
        user_id = serializer.validated_data['user_id']
        try:
            user = User.objects.get(id=user_id)
            task.assigned_to = user
            task.save()

            # create a timeline event for task assignment
            TimelineEvent.objects.create(
                project=task.project,
                event_type='task_assigned',
                user=request.user,
                description=f"Task '{task.title}' assigned to {user.username}."
            )

            # create a notification for the assigned user
            Notification.objects.create(
                user=user,
                title=f"New Task Assigned: {task.title}",
                message=f"You have been assigned a new task: {task.title} in project {task.project.name}.",
                is_read=False
            )
            return Response(TaskSerializer(task).data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User does not exist."}, status=status.HTTP_404_NOT_FOUND)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Document Views
class DocumentListCreateView(generics.ListCreateAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project_id = self.request.query_params.get('project', None)
        queryset = Document.objects.filter(
            project__in=Project.objects.filter(
                models.Q(created_by=self.request.user) | 
                models.Q(members=self.request.user)
            )
        )
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset
    
    def perform_create(self, serializer):
        document = serializer.save(uploaded_by=self.request.user)

        # create a timeline event for document upload
        TimelineEvent.objects.create(
            project=document.project,
            event_type='document_uploaded',
            user=self.request.user,
            description=f"Document '{document.name}' uploaded to project '{document.project.name}'."
        )


class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(
            project__in=Project.objects.filter(
                models.Q(created_by=self.request.user) | 
                models.Q(members=self.request.user)
            )
        )
    

# Comment Views
class CommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project_id = self.request.query_params.get('project', None)
        task_id = self.request.query_params.get('task', None)
        
        queryset = Comment.objects.filter(
            models.Q(project__created_by=self.request.user) |
            models.Q(project__members=self.request.user) |
            models.Q(task__project__created_by=self.request.user) |
            models.Q(task__project__members=self.request.user)
        ).distinct()
        
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        
        return queryset

    def perform_create(self, serializer):
        comment = serializer.save(author=self.request.user)
        # Create timeline event
        project = comment.project or comment.task.project
        TimelineEvent.objects.create(
            project=project,
            event_type='comment_added',
            description=f'Comment was added by {self.request.user.username}',
            user=self.request.user
        )

class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Comment.objects.filter(author=self.request.user)

# Timeline Views
class TimelineEventListView(generics.ListAPIView):
    serializer_class = TimelineEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project_id = self.request.query_params.get('project', None)
        queryset = TimelineEvent.objects.filter(
            project__in=Project.objects.filter(
                models.Q(created_by=self.request.user) | 
                models.Q(members=self.request.user)
            )
        )
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset

# Notification Views
class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(
        Notification, 
        id=notification_id, 
        user=request.user
    )
    notification.is_read = True
    notification.save()
    return Response(NotificationSerializer(notification).data)


