
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import generics
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.contrib.auth import authenticate
from .models import Project, Job, Agent, Issue, Commit

from gamification.models import UserProfile
import os
import anthropic
import json
import requests
import threading
from gamification.serializers import UserProfileSerializer
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    ProjectSerializer,
    JobSerializer,
    IssueSerializer,
    AgentSerializer,
    CommitSerializer,
    JobAssignmentSerializer,
    AgentJobRequestSerializer,
    AgentJobStartSerializer,
    AgentJobProgressSerializer,
    AgentJobCompleteSerializer,
    ToolCallbackSerializer,
    AgentTelemetrySerializer,
    AgentHeartbeatSerializer,
)
from quiz.models import Topic, Question, QuizSession

class HealthCheck(APIView):
    def get(self, request):
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'detail': '아이디와 비밀번호를 입력해 주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, username=username, password=password)

        if user is None:
            return Response(
                {'detail': '계정 정보가 올바르지 않습니다.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def post(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
        }, status=status.HTTP_201_CREATED)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)

class ConfigView(APIView):
    def get(self, request):
        # Placeholder for actual configuration
        config_data = {
            'version': '1.0.0',
            'flags': {
                'feature_a_enabled': True,
                'feature_b_enabled': False,
            }
        }
        return Response(config_data)

class ProjectRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProjectSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AgentJobRequestView(APIView):
    def post(self, request):
        serializer = AgentJobRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        agent_id = data['agent_id']
        capabilities = data.get('capabilities', [])
        agent_status = data.get('status', 'idle')
        agent_version = data.get('agent_version')
        max_jobs = data.get('max_jobs', 1)

        defaults = {
            'capabilities': capabilities,
            'status': agent_status,
            'last_heartbeat': timezone.now(),
        }
        if agent_version:
            defaults['version'] = agent_version

        agent, _ = Agent.objects.update_or_create(agent_id=agent_id, defaults=defaults)

        # repository_analysis와 code_generation 모두 pending 상태로 필터링
        pending_jobs = list(Job.objects.filter(status='pending', job_type='repository_analysis').order_by('created_at')[:max_jobs])
        if not pending_jobs:
            # 대기할 job이 없으므로 204 No Content 반환
            return Response(status=status.HTTP_204_NO_CONTENT)

        assignments = []
        now = timezone.now()
        for job in pending_jobs:
            job.agent = agent
            job.status = 'assigned'
            job.assigned_at = now
            job.save(update_fields=['agent', 'status', 'assigned_at', 'updated_at'])
            assignments.append(JobAssignmentSerializer(job).data)

        agent.current_job_id = str(assignments[0]['job_id'])
        agent.status = 'assigned'
        agent.save(update_fields=['current_job_id', 'status'])

        return Response({'jobs': assignments}, status=status.HTTP_200_OK)


class AgentJobStartView(APIView):
    def post(self, request, job_id):
        serializer = AgentJobStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = get_object_or_404(Job, id=job_id)

        agent_id = serializer.validated_data.get('agent_id')
        if job.agent and agent_id and job.agent.agent_id != agent_id:
            return Response({'detail': 'Job is assigned to a different agent.'}, status=status.HTTP_409_CONFLICT)

        start_time = serializer.validated_data.get('start_time') or timezone.now()
        job.status = 'running'
        job.started_at = start_time
        job.save(update_fields=['status', 'started_at', 'updated_at'])

        if job.agent:
            job.agent.status = 'processing'
            job.agent.current_job_id = str(job.id)
            job.agent.last_heartbeat = timezone.now()
            job.agent.save(update_fields=['status', 'current_job_id', 'last_heartbeat'])

        return Response(
            {'job_id': job.id, 'status': job.status, 'started_at': job.started_at.isoformat()},
            status=status.HTTP_200_OK,
        )


class AgentJobProgressView(APIView):
    def post(self, request, job_id):
        serializer = AgentJobProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = get_object_or_404(Job, id=job_id)

        progress_entry = {
            'timestamp': timezone.now().isoformat(),
            'log_message': serializer.validated_data.get('log_message'),
            'intermediate_artifact': serializer.validated_data.get('intermediate_artifact'),
        }
        if 'percent_complete' in serializer.validated_data:
            progress_entry['percent_complete'] = float(serializer.validated_data['percent_complete'])

        progress_entry = {key: value for key, value in progress_entry.items() if value is not None}

        current_log = list(job.progress_log or [])
        current_log.append(progress_entry)
        job.progress_log = current_log
        job.save(update_fields=['progress_log', 'updated_at'])
        return Response(status=status.HTTP_202_ACCEPTED)


class AgentJobCompleteView(APIView):
    def post(self, request, job_id):
        serializer = AgentJobCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = get_object_or_404(Job, id=job_id)

        status_value = serializer.validated_data.get('status', 'success')
        job.status = status_value
        job.summary = serializer.validated_data.get('summary')
        job.final_result_url = serializer.validated_data.get('final_result_url')
        job.error_message = serializer.validated_data.get('error_message')
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'summary', 'final_result_url', 'error_message', 'completed_at', 'updated_at'])

        if job.agent:
            job.agent.status = 'idle' if status_value == 'success' else 'error'
            job.agent.current_job_id = None
            job.agent.last_heartbeat = timezone.now()
            job.agent.save(update_fields=['status', 'current_job_id', 'last_heartbeat'])

        return Response({'job_id': job.id, 'status': job.status}, status=status.HTTP_200_OK)


class AgentToolCallbackView(APIView):
    def post(self, request):
        serializer = ToolCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        run_id = data['run_id']
        try:
            job = Job.objects.get(id=int(run_id))
        except (ValueError, Job.DoesNotExist):
            return Response({'detail': 'Job not found for run_id.'}, status=status.HTTP_404_NOT_FOUND)

        invocation_entry = {
            'timestamp': timezone.now().isoformat(),
            'tool_name': data['tool_name'],
            'tool_input': data.get('tool_input'),
            'tool_output': data.get('tool_output'),
        }
        invocations = list(job.tool_invocations or [])
        invocations.append(invocation_entry)
        job.tool_invocations = invocations
        job.save(update_fields=['tool_invocations', 'updated_at'])
        return Response(status=status.HTTP_202_ACCEPTED)


class AgentTelemetryView(APIView):
    def post(self, request):
        serializer = AgentTelemetrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        agent, _ = Agent.objects.get_or_create(agent_id=data['agent_id'])
        agent.telemetry = {
            'metrics': data['metrics'],
            'received_at': timezone.now().isoformat(),
        }
        agent.last_heartbeat = timezone.now()
        agent.save(update_fields=['telemetry', 'last_heartbeat'])
        return Response(status=status.HTTP_202_ACCEPTED)


class AgentHeartbeatView(APIView):
    def post(self, request):
        serializer = AgentHeartbeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        defaults = {
            'status': data['status'],
            'last_heartbeat': timezone.now(),
        }
        if data.get('agent_version'):
            defaults['version'] = data['agent_version']
        if 'current_job_id' in data:
            defaults['current_job_id'] = data['current_job_id'] or None

        agent, _ = Agent.objects.update_or_create(
            agent_id=data['agent_id'],
            defaults=defaults,
        )
        return Response({'agent_id': agent.agent_id, 'status': agent.status}, status=status.HTTP_200_OK)


class ProjectScanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        project.file_tree = request.data.get('file_tree')
        project.language_stats = request.data.get('language_stats')
        project.total_loc = request.data.get('total_loc')
        project.avg_complexity = request.data.get('avg_complexity')
        project.save()

        return Response(status=status.HTTP_200_OK)

    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        project.file_tree = request.data.get('file_tree')
        project.language_stats = request.data.get('language_stats')
        project.total_loc = request.data.get('total_loc')
        project.avg_complexity = request.data.get('avg_complexity')
        project.save()

        return Response(status=status.HTTP_200_OK)

class ProjectIssuesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        issues_data = request.data.get('issues', [])
        analyzer = request.data.get('analyzer')

        for issue_data in issues_data:
            Issue.objects.create(
                project=project,
                analyzer=analyzer,
                file=issue_data.get('file'),
                line=issue_data.get('line'),
                rule_id=issue_data.get('rule_id'),
                severity=issue_data.get('severity'),
                message=issue_data.get('message'),
            )

        return Response(status=status.HTTP_201_CREATED)

class ProjectReadmeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        project.readme_content = request.data.get('content')
        project.save()

        return Response(status=status.HTTP_200_OK)

class ProjectCommitsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        commit_data = request.data
        commit_data['project'] = project.id

        serializer = CommitSerializer(data=commit_data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CreateAgentJobView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        job_type = request.data.get('job_type')
        payload = request.data.get('payload', {})

        if not job_type:
            return Response({'error': 'job_type is required'}, status=status.HTTP_400_BAD_REQUEST)

        # payload에 project 정보 추가 (agent가 올바른 repo 경로를 사용하도록)
        if 'project' not in payload:
            payload['project'] = {
                'id': project.id,
                'name': project.name,
                'local_path': project.local_path,
                'remote_url': project.remote_url,
            }

        job = Job.objects.create(
            project=project,
            job_type=job_type,
            payload=payload,
            status='pending'
        )
        serializer = JobSerializer(job)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class JobDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id, job_id):
        job = get_object_or_404(Job, id=job_id, project_id=project_id)

        # 처음 조회할 때 job 타입에 따라 처리 (pending 상태인 경우)
        if job.status == 'pending' and not job.summary:
            if job.job_type == 'code_generation':
                # 상태를 미리 running으로 설정하여 중복 스레드 방지
                job.status = 'running'
                job.started_at = timezone.now()
                job.progress_log = (job.progress_log or []) + [
                    {'percent_complete': 5, 'log_message': f'{job.job_type} 작업 시작...'}
                ]
                job.save(update_fields=['status', 'started_at', 'progress_log', 'updated_at'])
                threading.Thread(target=self._generate_code, args=(job,), daemon=True).start()
            elif job.job_type == 'repository_analysis':
                # ✅ 수정: Agent가 처리하도록 상태를 'assigned'로 변경
                # (Agent의 /agent/jobs/request에서 'assigned' 상태의 job을 반환하도록 요청)
                # repository_analysis는 Agent가 처리해야 하므로 queued 상태로 유지하지 않고
                # 상태를 초기화하여 Agent가 다시 요청할 수 있도록 함
                logs = job.progress_log or []
                if not logs:
                    logs = [{'percent_complete': 5, 'log_message': 'repository_analysis 작업을 Agent에 할당 중...'}]

                # 무한 루프 방지: 같은 상태가 반복되지 않도록 로그 체크
                has_init_log = any(
                    entry.get('log_message') == 'repository_analysis 작업을 Agent에 할당 중...'
                    for entry in logs
                )
                if not has_init_log:
                    logs.append({'percent_complete': 10, 'log_message': 'repository_analysis 작업을 Agent에 할당 중...'})

                job.progress_log = logs
                # ⭐ 중요: status를 pending으로 유지하여 Agent가 /agent/jobs/request에서 가져갈 수 있도록
                # (AgentJobRequestView에서 pending 상태의 job을 assigned로 변경함)
                job.save(update_fields=['progress_log', 'updated_at'])
            else:
                job.status = 'failed'
                job.error_message = f'Unknown job type: {job.job_type}'
                job.save(update_fields=['status', 'error_message'])

        serializer = JobSerializer(job)
        return Response(serializer.data)

    def _generate_code(self, job):
        """코드 생성 (Anthropic 또는 OpenAI) - code_generation job만 처리"""
        try:
            # code_generation job만 처리
            if job.job_type != 'code_generation':
                job.status = 'failed'
                job.error_message = f'This method only handles code_generation jobs, not {job.job_type}'
                job.save()
                return

            payload = job.payload or {}
            prompt = payload.get('prompt', '')
            language = payload.get('language', 'python')

            if not prompt:
                job.status = 'failed'
                job.error_message = 'Prompt is required'
                job.save()
                return

            # 진행 상태 로그 시작
            job.status = 'running'
            job.started_at = timezone.now()
            job.progress_log = [
                {'percent_complete': 10, 'log_message': f'{language.upper()} 코드 생성 준비 중...'},
            ]
            job.save()

            # 진행 상황 업데이트
            job.progress_log.append({'percent_complete': 30, 'log_message': '모델 API에 요청 중...'})
            job.save()

            # 공통 시스템 프롬프트
            system_prompt = (
                f"You are an expert {language} programmer. Generate production-ready code based on the user's request.\n\n"
                f"Requirements:\n"
                f"- Write clean, well-commented code\n"
                f"- Follow {language} best practices\n"
                f"- Include error handling where appropriate\n"
                f"- Return ONLY the code, no explanation or markdown formatting"
            )

            provider = os.getenv('CODEGEN_PROVIDER', 'anthropic').lower()
            generated_code = None

            if provider == 'langchain':
                # LangChain 서버 호출 경로
                base_url = os.getenv('LANGCHAIN_BASE_URL', '').rstrip('/')
                route = os.getenv('LANGCHAIN_ROUTE', '/generate')
                url = f"{base_url}{route}" if base_url else ''
                if not url:
                    raise RuntimeError('LANGCHAIN_BASE_URL 가 설정되지 않았습니다.')
                headers = {'Content-Type': 'application/json'}
                api_key = os.getenv('LANGCHAIN_API_KEY')
                if api_key:
                    headers['Authorization'] = f"Bearer {api_key}"
                body = {
                    'prompt': prompt,
                }
                # 진행 로그 업데이트
                job.progress_log.append({'percent_complete': 40, 'log_message': f'LangChain 서버 요청: {url}'})
                job.save()
                r = requests.post(url, json=body, headers=headers, timeout=60)
                if r.status_code >= 400:
                    raise RuntimeError(f"LangChain error {r.status_code}: {r.text}")
                # 응답 형태: {"rewritten": str, "code": str}
                data = r.json() if r.headers.get('Content-Type','').startswith('application/json') else {}
                generated_code = (
                    data.get('code')
                    or (data.get('result') or {}).get('code')
                    or data.get('content')
                    or r.text
                )
                if not generated_code:
                    raise RuntimeError('LangChain 응답에 code가 없습니다.')
            elif provider == 'openai':
                # OpenAI 경로
                from openai import OpenAI
                oa_model = os.getenv('OPENAI_CODEGEN_MODEL', 'gpt-4o-mini')
                oa_client = OpenAI()
                oa_resp = oa_client.chat.completions.create(
                    model=oa_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=2000,
                    temperature=0.2,
                )
                generated_code = (oa_resp.choices[0].message.content or '').strip()
            else:
                # Anthropic 경로
                an_model = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-latest')
                try:
                    client = anthropic.Anthropic()
                    response = client.messages.create(
                        model=an_model,
                        max_tokens=2000,
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                        system=system_prompt
                    )
                    generated_code = response.content[0].text if response.content else ''
                except Exception as ae:
                    err_text = str(ae)
                    # 모델 미존재/미할당 오류 시 OpenAI로 폴백 (OPENAI_API_KEY가 존재할 때)
                    if os.getenv('OPENAI_API_KEY') and ('not_found' in err_text or '404' in err_text or 'model' in err_text):
                        job.progress_log.append({'percent_complete': 50, 'log_message': 'Anthropic 모델 미가용: OpenAI로 폴백 중...'})
                        job.save()
                        try:
                            from openai import OpenAI
                            oa_model = os.getenv('OPENAI_CODEGEN_MODEL', 'gpt-4o-mini')
                            oa_client = OpenAI()
                            oa_resp = oa_client.chat.completions.create(
                                model=oa_model,
                                messages=[
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": prompt},
                                ],
                                max_tokens=2000,
                                temperature=0.2,
                            )
                            generated_code = (oa_resp.choices[0].message.content or '').strip()
                        except Exception as oe:
                            raise oe
                    else:
                        raise ae

            # 진행 상황 업데이트
            job.progress_log.append({'percent_complete': 75, 'log_message': '코드 생성 완료, 최종 처리 중...'})
            job.save()

            # 최종 상태 업데이트
            job.progress_log.append({'percent_complete': 100, 'log_message': '✓ 코드 생성 완료!'})
            job.status = 'completed'
            job.summary = generated_code
            job.completed_at = timezone.now()
            job.save()

        except Exception as e:
            error_msg = str(e)
            job.status = 'failed'
            job.error_message = error_msg
            job.progress_log = [
                {'percent_complete': 0, 'log_message': f'⚠ 오류 발생: {error_msg}'}
            ]
            job.save()


class ProjectListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # For simplicity, returning all projects. In a real app, you'd filter by user.
        projects = Project.objects.all()
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data)


class DeviceLoginView(APIView):
    def post(self, request):
        # Placeholder for device login logic
        return Response({'status': 'device login successful'}, status=status.HTTP_200_OK)

class DeviceUpdatesView(APIView):
    def get(self, request):
        # Placeholder for device updates logic
        return Response({'version': '1.0.1', 'notes': 'Bug fixes and performance improvements.'}, status=status.HTTP_200_OK)

class TasksAssignedView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        # Placeholder for tasks assigned logic
        return Response({'tasks': []}, status=status.HTTP_200_OK)

class UploadsView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        # Placeholder for uploads logic
        return Response({'status': 'upload successful'}, status=status.HTTP_201_CREATED)

class ActivityLogsView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        # Placeholder for activity logs logic
        print(request.data)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MobileLoginView(APIView):
    def post(self, request):
        # Placeholder for mobile login logic
        return Response({'token': 'dummy-token'}, status=status.HTTP_200_OK)

class MobileFeedView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        # Placeholder for mobile feed logic
        return Response({'feed': []}, status=status.HTTP_200_OK)

class MobileFeedbackView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        # Placeholder for mobile feedback logic
        print(request.data)
        return Response(status=status.HTTP_201_CREATED)

class NotificationsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        # Placeholder for notifications logic
        return Response({'notifications': []}, status=status.HTTP_200_OK)

class NotificationsTokenView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        # Placeholder for notifications token logic
        print(request.data)
        return Response(status=status.HTTP_204_NO_CONTENT)


from quiz.models import Topic as QuizTopic
from quiz.serializers import QuizPoolSerializer, GeneratedQuizSerializer

# Quiz Engine Views
class QuizPoolsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        queryset = QuizTopic.objects.all()
        serializer = QuizPoolSerializer(queryset, many=True)
        return Response({'pools': serializer.data}, status=status.HTTP_200_OK)

from quiz.models import QuizProfile
from quiz.serializers import QuizSessionDetailSerializer

class QuizSessionsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pool_id = request.data.get('pool_id')
        num_questions = request.data.get('num_questions', 10)

        try:
            topic = Topic.objects.get(id=pool_id)
        except Topic.DoesNotExist:
            return Response({'error': 'Quiz pool not found.'}, status=status.HTTP_404_NOT_FOUND)

        profile, _ = QuizProfile.objects.get_or_create(user=request.user)

        session = QuizSession.objects.create(profile=profile)

        questions = Question.objects.filter(topic=topic).order_by('?')[:num_questions]
        session.questions.set(questions)

        serializer = QuizSessionDetailSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class QuizSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, session_id):
        session = get_object_or_404(QuizSession, id=session_id)
        serializer = QuizSessionDetailSerializer(session)
        return Response(serializer.data)

from quiz.serializers import QuizPoolSerializer, QuizSessionDetailSerializer, SessionAnswerSubmitSerializer, AnswerSerializer, SessionAnswerSubmitSerializer, AnswerSerializer
from quiz.models import Topic, Question, QuizSession, SessionAnswer

class QuizSessionAnswersView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        serializer = SessionAnswerSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        question_id = data['question_id']
        selected_option_id = data['selected_option_id']

        session = get_object_or_404(QuizSession, id=session_id)
        question = get_object_or_404(Question, id=question_id)

        is_correct = (str(question.correct_answer) == str(selected_option_id))

        SessionAnswer.objects.create(
            session=session,
            question=question,
            user_answer=selected_option_id,
            is_correct=is_correct
        )

        if is_correct:
            session.score += 10  # Add 10 points for a correct answer
            session.save()

        answer_data = AnswerSerializer(question).data
        return Response({
            'is_correct': is_correct,
            'answer': answer_data
        })

from django.utils import timezone

class QuizSessionFinishView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, session_id):
        session = get_object_or_404(QuizSession, id=session_id)
        session.is_finished = True
        session.end_time = timezone.now()
        session.save()

        return Response({
            'session_id': session.id,
            'score': session.score,
            'finished_at': session.end_time
        }, status=status.HTTP_200_OK)

class QuizHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response({'history': []}, status=status.HTTP_200_OK)

class QuizRecommendationsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response({'recommendations': []}, status=status.HTTP_200_OK)

class QuizGeneratedSaveView(APIView):
    """
    Saves LLM-generated quizzes (e.g., from code generation) into the Django DB.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GeneratedQuizSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        obj = serializer.save()
        return Response(
            {
                'id': obj.id,
                'source': obj.source,
                'question_count': len(obj.questions or []),
                'created_at': obj.created_at,
            },
            status=status.HTTP_201_CREATED,
        )

from gamification.models import UserProfile as GamiUserProfile
from gamification.serializers import UserProfileSerializer as GamiProfileSerializer

# Gamification Engine Views
class GamiProfileView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        profile, _ = GamiUserProfile.objects.get_or_create(user=request.user)
        serializer = GamiProfileSerializer(profile)
        return Response(serializer.data)

class GamiEventsView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        print(request.data)
        return Response(status=status.HTTP_201_CREATED)

from gamification.models import Badge as GamiBadge
from gamification.serializers import BadgeSerializer as GamiBadgeSerializer

class GamiBadgesView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        badges = GamiBadge.objects.filter(is_active=True)
        serializer = GamiBadgeSerializer(badges, many=True, context={'request': request})
        return Response({'badges': serializer.data})

class GamiRedeemView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        return Response({'status': 'redeemed'}, status=status.HTTP_200_OK)

from gamification.serializers import UserProfileSerializer, BadgeSerializer, LeaderboardEntrySerializer, LeaderboardEntrySerializer

class GamiLeaderboardView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        leaderboard_users = GamiUserProfile.objects.order_by('-xp')[:10]
        
        data = []
        for i, profile in enumerate(leaderboard_users):
            data.append({
                'rank': i + 1,
                'user': profile.user,
                'score': profile.xp
            })

        # We are manually constructing the data, so we can just return it.
        # For more complex cases, a serializer would be better.
        # In this case, let's build a simple dictionary to match the frontend expectations.
        
        response_data = []
        for entry in data:
            response_data.append({
                'rank': entry['rank'],
                'username': entry['user'].username,
                'score': entry['score'],
                'isCurrentUser': entry['user'] == request.user
            })

        return Response({'leaderboard': response_data})
