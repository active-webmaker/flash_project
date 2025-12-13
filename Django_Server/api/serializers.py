import copy
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Project, Agent, Job, Issue, Commit


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)


class RegisterSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'local_path', 'remote_url', 'created_at']


class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = [
            'agent_id',
            'status',
            'capabilities',
            'version',
            'current_job_id',
            'telemetry',
            'last_heartbeat',
        ]


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            'id',
            'agent',
            'project',
            'status',
            'job_type',
            'payload',
            'assigned_at',
            'summary',
            'final_result_url',
            'error_message',
            'progress_log',
            'tool_invocations',
            'created_at',
            'started_at',
            'completed_at',
        ]


class IssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = '__all__'


class CommitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commit
        fields = '__all__'


class JobAssignmentSerializer(serializers.ModelSerializer):
    job_id = serializers.IntegerField(source='id')
    payload = serializers.SerializerMethodField()
    project = ProjectSerializer(read_only=True)

    class Meta:
        model = Job
        fields = [
            'job_id',
            'job_type',
            'status',
            'payload',
            'project',
            'created_at',
            'started_at',
            'completed_at',
        ]

    def get_payload(self, obj):
        payload = copy.deepcopy(obj.payload or {})
        project = obj.project
        project_context = None
        if project:
            project_context = {
                'id': project.id,
                'name': project.name,
                'local_path': project.local_path,
                'remote_url': project.remote_url,
            }
        payload.setdefault(
            'description',
            payload.get('prompt') or payload.get('title') or obj.job_type,
        )
        if project_context and 'project' not in payload:
            payload['project'] = project_context
        return payload


class AgentJobRequestSerializer(serializers.Serializer):
    agent_id = serializers.CharField(max_length=100)
    capabilities = serializers.ListField(child=serializers.CharField(), required=False)
    status = serializers.CharField(max_length=50, required=False, default='idle')
    max_jobs = serializers.IntegerField(min_value=1, default=1)
    agent_version = serializers.CharField(max_length=50, required=False, allow_blank=True)


class AgentJobStartSerializer(serializers.Serializer):
    agent_id = serializers.CharField(max_length=100, required=False)
    start_time = serializers.DateTimeField(required=False)


class AgentJobProgressSerializer(serializers.Serializer):
    log_message = serializers.CharField(required=False, allow_blank=True)
    percent_complete = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    intermediate_artifact = serializers.JSONField(required=False)


class AgentJobCompleteSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=50, required=False)
    summary = serializers.CharField(required=False, allow_blank=True)
    final_result_url = serializers.URLField(required=False, allow_blank=True)
    error_message = serializers.CharField(required=False, allow_blank=True)


class ToolCallbackSerializer(serializers.Serializer):
    run_id = serializers.CharField()
    tool_name = serializers.CharField()
    tool_input = serializers.JSONField()
    tool_output = serializers.JSONField(required=False)


class TelemetryMetricSerializer(serializers.Serializer):
    name = serializers.CharField()
    value = serializers.FloatField()
    model = serializers.CharField(required=False, allow_blank=True)
    tool = serializers.CharField(required=False, allow_blank=True)
    job_id = serializers.CharField(required=False, allow_blank=True)


class AgentTelemetrySerializer(serializers.Serializer):
    agent_id = serializers.CharField(max_length=100)
    metrics = TelemetryMetricSerializer(many=True)


class AgentHeartbeatSerializer(serializers.Serializer):
    agent_id = serializers.CharField(max_length=100)
    status = serializers.CharField(max_length=50)
    agent_version = serializers.CharField(max_length=50, required=False, allow_blank=True)
    current_job_id = serializers.CharField(max_length=64, required=False, allow_blank=True)
