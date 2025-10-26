from rest_framework import serializers
from django.contrib.auth.models import User  # o tu propio modelo

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_staff']
