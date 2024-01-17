from django.db import models


# Create your models here.

class Student(models.Model):
    username = models.CharField(max_length=200, verbose_name="username", primary_key=True)

    studentId = models.CharField(max_length=200, verbose_name="student_id")

    class Meta:
        db_table = 'student'
        verbose_name = 'student'
        verbose_name_plural = verbose_name


class LoginInfo(models.Model):
    username = models.CharField(max_length=200, verbose_name="username")
    loginTime = models.DateTimeField(verbose_name="loginTime", null=True)
    version = models.CharField(max_length=200, verbose_name="version")

    class Meta:
        db_table = 'login_info'
        verbose_name = 'login_info'
        verbose_name_plural = verbose_name


class Forbidden(models.Model):
    username = models.CharField(max_length=200, verbose_name="username", null=True)

    class Meta:
        db_table = 'forbidden'
        verbose_name = 'forbidden'
        verbose_name_plural = verbose_name


class SubjectNumber(models.Model):
    subject = models.IntegerField(verbose_name="subject")
    grade = models.IntegerField(verbose_name="grade")
    A = models.IntegerField(verbose_name="a")
    B = models.IntegerField(verbose_name="b")
    C = models.IntegerField(verbose_name="c")
    D = models.IntegerField(verbose_name="d")
    E = models.IntegerField(verbose_name="e")
    sum = models.IntegerField(verbose_name="sum")

    class Meta:
        db_table = 'subject_number'
        verbose_name = 'subject_number'
        verbose_name_plural = verbose_name


class White(models.Model):
    username = models.CharField(max_length=200, verbose_name="username")

    class Meta:
        db_table = 'white'
        verbose_name = 'white'
        verbose_name_plural = verbose_name


class Standby(models.Model):
    username = models.CharField(max_length=200, verbose_name="username", primary_key=True)
    loginTime = models.DateTimeField(verbose_name="loginTime")
    between = models.IntegerField(verbose_name='between')

    class Meta:
        db_table = 'standby'
        verbose_name = 'standby'
        verbose_name_plural = verbose_name


class Feedback(models.Model):
    sendTime = models.DateTimeField(verbose_name="sendTime")
    rate = models.IntegerField(verbose_name='rate')
    message = models.CharField(max_length=2000, verbose_name="message", null=True)

    class Meta:
        db_table = 'feedback'
        verbose_name = 'feedback'
        verbose_name_plural = verbose_name
