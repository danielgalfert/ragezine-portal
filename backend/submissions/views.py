from rest_framework import status, viewsets
from rest_framework.response import Response
from .models import Submission, SubmissionVisual
from .serializers import SubmissionSerializer


class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer

    def create(self, request, *args, **kwargs):
        print("request.data:", request.data)
        print("request.FILES:", request.FILES)
        print("visuals:", request.FILES.getlist("visuals"))

        data = request.data.copy()
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        submission = serializer.save()

        for image in request.FILES.getlist("visuals"):
            SubmissionVisual.objects.create(
                submission=submission,
                image=image,
            )

        output_serializer = self.get_serializer(submission)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)