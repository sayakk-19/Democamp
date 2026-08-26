from django.db import models

# Create your models here.
class player(models.Model):
    Name = models.CharField(max_length=50)
    Email = models.EmailField()
    Passwd = models.CharField(max_length=80)
    Age = models.IntegerField()
    Position = models.CharField(max_length=30)
    Phno = models.IntegerField()
    appr = models.IntegerField()
    class Meta:
        db_table="player"

class Register(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField()
    phno = models.IntegerField()
    pwd = models.CharField(max_length=80)
    reenter_pwd = models.CharField(max_length=80)
    age = models.IntegerField()
    position = models.CharField(max_length=30)
    appr = models.IntegerField()
    class Meta:
        db_table="Register"
    def __str__(self):
        return self.name

