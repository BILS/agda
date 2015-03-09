from functools import wraps

from django.test import TestCase
from django.test.utils import override_settings
from django.core.urlresolvers import reverse

from profiles.models import AgdaUser
from mdr.models import MDRScanJob


fake_slug = 'asdfasdfasdfasdfasdf'


def with_two_jobs(orig):
    @wraps(orig)
    def wrapper(self):
        self._job1 = MDRScanJob.objects.create(name='Egg number one', status=10, scheduler_id=12)
        self._job2 = MDRScanJob.objects.create(name='Egg number two')
        self._job2.user = self.user
        self._job2.save()

        orig(self)

        # Cleanup
        for job in self._job1, self._job2:
            if MDRScanJob.objects.filter(pk=job.id).exists:
                job.delete()
    return wrapper


@override_settings(LOGGING={'handlers': {'development': {'level': 'ERROR'}}})
class TestJobViews(TestCase):
    def setUp(self):
        self.user = AgdaUser.objects.create_user('test@example.com', password='asdf')

    def login(self):
        self.client.login(username='test@example.com', password='asdf')

    @property
    def job1(self):
        if MDRScanJob.objects.filter(pk=self._job1.id).exists:
            return MDRScanJob.objects.get(pk=self._job1.id)
        return None

    @property
    def job2(self):
        if MDRScanJob.objects.filter(pk=self._job2.id).exists:
            return MDRScanJob.objects.get(pk=self._job2.id)
        return None

    def test_list_jobs_when_not_logged_in(self):
        url = reverse("jobs.views.list_jobs")
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

    @with_two_jobs
    def test_list_jobs_when_logged_in(self):
        self.login()
        response = self.client.get(reverse("jobs.views.list_jobs"))
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Egg number two')

    @with_two_jobs
    def test_view_job_when_not_logged_in(self):
        url = reverse("jobs.views.show_results", args=[self.job1.slug])
        response = self.client.get(url)
        self.assertContains(response, 'Egg number one')

        url = reverse("jobs.views.show_results", args=[self.job2.slug])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Egg number two')
        self.assertNotContains(response, 'Take')

    @with_two_jobs
    def test_view_job_when_logged_in(self):
        self.login()
        url = reverse("jobs.views.show_results", args=[self.job1.slug])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Egg number one')
        self.assertContains(response, 'Take')

        url = reverse("jobs.views.show_results", args=[self.job2.slug])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Egg number two')
        self.assertNotContains(response, 'Take')

    @with_two_jobs
    def test_get_unexisting_job(self):
        url = reverse("jobs.views.show_results", args=[fake_slug])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 404)

    @with_two_jobs
    def test_delete_job_when_not_logged_in(self):
        url = reverse("jobs.views.delete_job", args=[self.job1.slug])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Confirm job deletion')

        response = self.client.post(url)
        self.assertEquals(response.status_code, 302)

        url = reverse("jobs.views.delete_job", args=[self.job2.slug])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'This job is not yours')

        response = self.client.post(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'This job is not yours')

    @with_two_jobs
    def test_delete_job_when_logged_in(self):
        self.login()

        url = reverse("jobs.views.delete_job", args=[self.job1.slug])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Confirm job deletion')

        response = self.client.post(url)
        self.assertEquals(response.status_code, 302)

        url = reverse("jobs.views.delete_job", args=[self.job2.slug])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Confirm job deletion')

        response = self.client.post(url)
        self.assertEquals(response.status_code, 302)

    @with_two_jobs
    def test_show_deleted_job(self):
        url = reverse("jobs.views.delete_job", args=[self.job1.slug])
        url_show = reverse("jobs.views.show_results", args=[self.job1.slug])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Confirm job deletion')
        self.assertEquals(self.job1.is_alive, True)

        response = self.client.post(url)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(self.job1.is_alive, False)

        response = self.client.get(url_show)
        self.assertEquals(response.status_code, 404)

    @with_two_jobs
    def test_delete_deleted_job(self):
        url = reverse("jobs.views.delete_job", args=[self.job1.slug])

        response = self.client.post(url)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(self.job1.is_alive, False)

        response = self.client.get(url)
        self.assertEquals(response.status_code, 404)
        response = self.client.post(url)
        self.assertEquals(response.status_code, 404)

    @with_two_jobs
    def test_take_job(self):
        self.login()
        url = reverse("jobs.views.take_job", args=[self.job1.slug])

        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Take ownership of job')

        self.assertEquals(self.job1.user, None)
        response = self.client.post(url)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(self.job1.user, self.user)

    @with_two_jobs
    def test_take_deleted_job(self):
        self.login()
        url = reverse("jobs.views.delete_job", args=[self.job1.slug])

        response = self.client.post(url)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(self.job1.is_alive, False)

        url = reverse("jobs.views.take_job", args=[self.job1.slug])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 404)

        response = self.client.post(url)
        self.assertEquals(response.status_code, 404)

    @with_two_jobs
    def test_rename_job_anonymous(self):
        url = reverse("jobs.views.rename_job", args=[self.job1.slug])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "This job is not yours.")

        response = self.client.post(url, {'name': 'Egg number 88'})
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "This job is not yours.")
        self.assertEquals(self.job1.name, 'Egg number one')

        url = reverse("jobs.views.rename_job", args=[self.job2.slug])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "This job is not yours.")

        response = self.client.post(url, {'name': 'Egg number 88'})
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "This job is not yours.")
        self.assertEquals(self.job2.name, 'Egg number two')

    @with_two_jobs
    def test_rename_job_logged_in(self):
        self.login()
        url = reverse("jobs.views.rename_job", args=[self.job1.slug])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "This job is not yours.")

        url = reverse("jobs.views.rename_job", args=[self.job2.slug])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertNotContains(response, "This job is not yours.")

        response = self.client.post(url, {'name': 'Egg number 3'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(self.job2.name, 'Egg number 3')

    @with_two_jobs
    def test_delete_jobs_anonymous(self):
        url = reverse("jobs.views.delete_jobs")
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

        response = self.client.post(url, {'slug': [self.job1.slug]})
        self.assertEquals(response.status_code, 302)
        response = self.client.get('/')
        self.assertContains(response, 'The jobs have been deleted')

        response = self.client.post(url, {'slug': [self.job2.slug]})
        self.assertEquals(response.status_code, 302)
        response = self.client.get('/')
        self.assertContains(response, 'You cannot delete jobs that belong to someone else.')

        response = self.client.post(url, {'slug': [self.job1.slug, self.job2.slug]})
        self.assertEquals(response.status_code, 302)
        response = self.client.get('/')
        self.assertContains(response, 'You cannot delete jobs that belong to someone else.')

        response = self.client.post(url, {'slug': [self.job1.slug, self.job2.slug, fake_slug]})
        self.assertEquals(response.status_code, 404)

    @with_two_jobs
    def test_delete_jobs_logged_in(self):
        self.login()

        url = reverse("jobs.views.delete_jobs")
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

        response = self.client.post(url, {'slug': [self.job1.slug]})
        self.assertEquals(response.status_code, 302)
        response = self.client.get('/')
        self.assertContains(response, 'The jobs have been deleted')

        response = self.client.post(url, {'slug': [self.job2.slug]})
        self.assertEquals(response.status_code, 302)
        response = self.client.get('/')
        self.assertContains(response, 'The jobs have been deleted')

        response = self.client.post(url, {'slug': [self.job1.slug, self.job2.slug]})
        self.assertEquals(response.status_code, 302)
        response = self.client.get('/')
        self.assertContains(response, 'The jobs have been deleted')

        response = self.client.post(url, {'slug': [self.job1.slug, self.job2.slug, fake_slug]})
        self.assertEquals(response.status_code, 404)
