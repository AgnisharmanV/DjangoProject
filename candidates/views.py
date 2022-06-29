from django.views import View
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from .models import Candidate
import json
import boto3
import os
import re


@method_decorator(csrf_exempt, name='dispatch')
class CandidateRepo(View):

    def get(self, request):
        request_uri = request.build_absolute_uri()
        get_params = request.GET
        location = get_params.get('location', '')
        tech_skills = get_params.getlist('tech_skills', '')
        page_no = get_params.get('page_no', '')
        if not page_no:
            page_no = 1
            if location or tech_skills:
                request_uri += '&page_no=1'
            else:
                request_uri = request_uri[:-1] + '&page_no=1'

        candidate_records = Candidate.objects.all().order_by('id')
        if location:
            candidate_records = candidate_records.filter(location=location)
        if tech_skills:
            if len(tech_skills) == 1:
                tech_skills = tech_skills[0].split(',')
            tech_skills = [t.lower() for t in tech_skills]
            if 'python' in tech_skills:
                candidate_records = candidate_records.filter(tech_skills__Python=True)
            if 'node' in tech_skills:
                candidate_records = candidate_records.filter(tech_skills__Node=True)
            if 'java' in tech_skills:
                candidate_records = candidate_records.filter(tech_skills__Java=True)
            if 'ruby' in tech_skills:
                candidate_records = candidate_records.filter(tech_skills__Ruby=True)
            if 'docker' in tech_skills:
                candidate_records = candidate_records.filter(tech_skills__Docker=True)
            if 'js' in tech_skills:
                candidate_records = candidate_records.filter(tech_skills__JS=True)

        candidate_records = candidate_records[:50]
        paginated_records = Paginator(candidate_records, 10)

        data = {}
        num_of_pages = paginated_records.num_pages
        if int(page_no) > num_of_pages:
            return HttpResponse(f'Page number ({page_no}) exceeded the number of pages ({num_of_pages})')
        data['num_of_pages'] = num_of_pages
        page = paginated_records.page(page_no)

        page_content = page.object_list.values()
        page_content = [pc for pc in page_content]

        data['CandidateRecords'] = page_content
        has_previous = page.has_previous()
        if has_previous:
            data['previous_page'] = re.sub('page_no=\d', f'page_no={page.previous_page_number()}', request_uri)
        has_next = page.has_next()
        if has_next:
            data['next_page'] = re.sub('page_no=\d', f'page_no={int(page_no) + 1}', request_uri)
        return JsonResponse(data, status=200, safe=False)

    def post(self, request):
        added_candidates = []
        skipped_candidates = []
        post_objects = json.loads(request.body.decode('utf-8'))
        if 'candidates' not in post_objects.keys():
            post_objects = {'candidates': [post_objects]}
        for post_object_dict in post_objects['candidates']:
            print(post_object_dict)
            name = post_object_dict.get('name')
            address = post_object_dict.get('address')
            if not address:
                address = ''
            phone_number = post_object_dict.get('phone_number')
            if not phone_number:
                phone_number = ''
            email = post_object_dict.get('email')
            if not email:
                email = ''
            location = post_object_dict.get('location')
            tech_skills = post_object_dict.get('tech_skills')
            if tech_skills:
                if type(tech_skills) == str:
                    tech_skills = tech_skills.split(',')
                tech_skills = [s.lower().strip() for s in tech_skills]
            else:
                tech_skills = ''

            if not name:
                skipped_candidates.append('Skipped candidate - Name cannot be blank.')
                continue

            if not location:
                skipped_candidates.append(f'Skipped candidate {name} - Location cannot be blank.')
                continue

            contact_details = {
                'phone_number': phone_number,
                'email': email
            }
            tech_skills = {
                'Python': 'python' in tech_skills,
                'Java': 'java' in tech_skills,
                'Ruby': 'ruby' in tech_skills,
                'Docker': 'docker' in tech_skills,
                'Node': 'node' in tech_skills,
                'JS': 'js' in tech_skills
            }
            candidate_data = {
                'name': name.title(),
                'address': address,
                'contact_details': contact_details,
                'location': location.lower(),
                'tech_skills': tech_skills
            }

            candidate = Candidate.objects.create(**candidate_data)
            added_candidates.append(f'Candidate {name} added with id-{candidate.id}')
        data = {}
        if added_candidates:
            data['AddedCandidates'] = added_candidates
        if skipped_candidates:
            data['SkippedCandidates'] = skipped_candidates
        return JsonResponse(data, status=201)


@method_decorator(csrf_exempt, name='dispatch')
class UserUtils(View):
    def get(self, request):
        user_ = get_user_model()
        users_ = user_.objects.all().values()
        user_data = []
        for u in users_:
            user_data.append(u['username'])
        return JsonResponse(user_data, status=200, safe=False)

    def post(self, request):
        added_users = []
        skipped_users = []
        user_objects = json.loads(request.body.decode('utf-8'))
        if 'users' not in user_objects.keys():
            user_objects = {'users': [user_objects]}
        for user in user_objects['users']:
            user_name = user.get('username')
            password = user.get('password')
            email = user.get('email')

            if not user_name:
                skipped_users.append(f'User skipped - username cannot be blank')
                continue

            if not password:
                skipped_users.append(f'User {user_name} skipped - password cannot be blank')
                continue

            user = User.objects.create_user(username=user_name,
                                            email=email,
                                            password=password)

            added_users.append(f'User {user_name} added.')

        data = {}
        if added_users:
            data['AddedUsers'] = added_users
        if skipped_users:
            data['SkippedUsers'] = skipped_users

        return JsonResponse(data, status=201)


@method_decorator(csrf_exempt, name='dispatch')
class SQSHandler(View):
    def post(self, request):
        candidate_id = json.loads(request.body.decode('utf-8'))['id']
        candidate_record = Candidate.objects.filter(id=candidate_id).values()
        candidate_record = str([c for c in candidate_record][0])

        access_key = os.getenv('aws_access_key_id')
        secret_key = os.getenv('aws_secret_access_key')
        queue_url = os.getenv('sqs_queue')

        try:
            sqs_client = boto3.client('sqs')
        except:
            if (not access_key) and (not secret_key):
                return HttpResponse('AWS credentials not configured.')
            else:
                sqs_client = boto3.client('sqs', aws_access_key_id=access_key,
                                          aws_secret_access_key=secret_key)

        if not queue_url:
            return HttpResponse('SQS QueueUrl not configured.')

        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=(
                candidate_record
            )
        )
        return JsonResponse(response, status=201)
