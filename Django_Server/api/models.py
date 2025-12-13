from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=255)
    local_path = models.CharField(max_length=1024)
    remote_url = models.CharField(max_length=1024, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    file_tree = models.JSONField(null=True, blank=True)
    language_stats = models.JSONField(null=True, blank=True)
    total_loc = models.IntegerField(null=True, blank=True)
    avg_complexity = models.FloatField(null=True, blank=True)
    readme_content = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class Agent(models.Model):
    agent_id = models.CharField(max_length=100, primary_key=True)
    status = models.CharField(max_length=50, default='idle')
    capabilities = models.JSONField(default=list)
    version = models.CharField(max_length=50, null=True, blank=True)
    current_job_id = models.CharField(max_length=64, null=True, blank=True)
    telemetry = models.JSONField(default=dict, blank=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.agent_id)


class Job(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    agent = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    job_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress_log = models.JSONField(default=list, blank=True)
    tool_invocations = models.JSONField(default=list, blank=True)
    summary = models.TextField(null=True, blank=True)
    final_result_url = models.URLField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'{self.job_type} - {self.status}'


class Issue(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    analyzer = models.CharField(max_length=100)
    file = models.CharField(max_length=1024)
    line = models.IntegerField()
    rule_id = models.CharField(max_length=255)
    severity = models.CharField(max_length=50)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.file}:{self.line} - {self.rule_id}'


class Commit(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    commit_hash = models.CharField(max_length=40, unique=True)
    author_email = models.EmailField()
    message = models.TextField()
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.commit_hash
