from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
import jwt, datetime

from Authentication.models import UserDetails, Student, Batch, Curriculum


# method_decorator(csrf_protect, name='dispatch')


class SignIn(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        # pushingData()
        data = self.request.data
        email = data['email']
        password = data['password']
        user = UserDetails.objects.filter(email=email).values()
        print(user.exists())
        if user.exists():
            user = user[0]
            user_password = user['encryptedPassword']
            if password == user_password:
                print(user["userId"])
                payload = {
                    "UserId": user["userId"],
                    "expiryTime": str(datetime.datetime.utcnow() + datetime.timedelta(minutes=60)),
                    "creationTime": str(datetime.datetime.utcnow())
                }
                secretKey = "BoltAbacus"
                loginToken = jwt.encode(payload, secretKey, algorithm='HS256')
                print(loginToken)
                response = Response({
                    "email": user["email"],
                    "role": user["role"],
                    "firstName": user["firstName"]
                },
                    status=status.HTTP_200_OK
                )
                response.set_cookie(key="token", value=loginToken)
                return response
            else:
                return Response({"message": "Invalid Password. Try Again"}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({"message": "Invalid Credentials. Try Again"}, status=status.HTTP_401_UNAUTHORIZED)


def pushingData():
    user = UserDetails.objects.create(
        firstName='anish',
        lastName='U',
        phoneNumber='9635404926',
        email='anishu@gmail.com',
        role='student',
        encryptedPassword='password1',
        created_date='2023-09-30',
        blocked=0
    )
    user.save()

    curriculum = Curriculum.objects.create(
        quizId=3,
        levelId=5,
        classId=3,
        topicId=2,
        quizType='Classwork',
        quizName='1stClasswork', )
    # curriculum.save()
    batch = Batch.objects.create(
        batchId=2,
        timeDay='Wednesday',
        timeSchedule='10:00AM',
        numberOfStudents=2,
        active=1,
        batchName='FirstBatch',
        latestLevelId=1,
        latestClass=curriculum,
        latestLink='www.google.com')

    batch.save()
    userStudentEntry = Student.objects.create(user=user, batch=batch)
    userStudentEntry.save()
    # print(batch, userStudentEntry, user, curriculum)


class CurrentLevels(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            idToken = request.headers['AUTH-TOKEN']
            if idToken is None:
                return Response({'expired': "tokenExpired"})
            secretKey = "BoltAbacus"
            payload = jwt.decode(idToken, secretKey, algorithms=['HS256'])
            userId = payload['UserId']
            userBatchDetails = Student.objects.filter(user=userId).values()[0]
            userBatchId = userBatchDetails['batch_id']
            userBatch = Batch.objects.filter(batchId=userBatchId).values()[0]
            latestLevel = userBatch['latestLevelId']
            latestLink = userBatch['latestLink']
            #join class link
            return Response({"levelId": latestLevel, "link": latestLink}, status=status.HTTP_200_OK)
        except Exception as e:
            Response({"Error Message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# @method_decorator(ensure_csrf_cookie, name='dispatch')
# class GetCSRFToken(APIView):
#     permission_classes = (permissions.AllowAny)
#
#     def get(self, request, format=None):
#         return Response({'success': 'CSRF cookie set'})

# Create your views here.
