from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator

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
    phno = models.CharField(max_length=10, validators=[
        RegexValidator(
            regex = r'^\d{10}$',
            message='Phone number must contain only digits.'
        )
    ])
    pwd = models.CharField(max_length=80)
    reenter_pwd = models.CharField(max_length=80)
    age = models.IntegerField(validators=[
        MinValueValidator(7, message="You must be at least 7 years old."),
        MaxValueValidator(50, message="Age cannot be greater than 50.")
    ])
    position = models.CharField(max_length=30)
    appr = models.IntegerField()
    class Meta:
        db_table="Register"
    def __str__(self):
        return self.name

