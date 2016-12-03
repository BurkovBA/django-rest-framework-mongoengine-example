from rest_framework import serializers
from rest_framework_mongoengine import serializers as mongoserializers

from models import Tool


class ToolSerializer(mongoserializers.DocumentSerializer):
    id = serializers.CharField(read_only=False)

    class Meta:
        model = Tool