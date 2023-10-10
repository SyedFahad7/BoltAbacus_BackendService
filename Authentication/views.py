import datetime
import jwt
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from Authentication.models import (UserDetails, Student,
                                   Batch, Curriculum,
                                   TopicDetails, QuizQuestions,
                                   Progress)


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
            user = user.first()
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
                    "firstName": user["firstName"],
                    "lastName": user["lastName"],
                    "token": loginToken
                },
                    status=status.HTTP_200_OK
                )
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


def IdExtraction(token):
    try:
        secretKey = "BoltAbacus"
        payload = jwt.decode(token, secretKey, algorithms=['HS256'])
        userId = payload['UserId']
        return userId
    except Exception as e:
        return e


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
            userBatchDetails = Student.objects.filter(user=userId).values().first()
            userBatchId = userBatchDetails['batch_id']
            userBatch = Batch.objects.filter(batchId=userBatchId).values().first()
            latestLevel = userBatch['latestLevelId']
            latestLink = userBatch['latestLink']
            latestClass = userBatch['latestClass_id']
            return Response({"levelId": latestLevel, "latestClass": latestClass, "latestLink": latestLink},
                            status=status.HTTP_200_OK)
        except Exception as e:
            Response({"Error Message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def pushTopicsData():
    TopicDetails.objects.all().delete()
    TopicDetails.objects.create(
        levelId=1,
        classId=1,
        topicId=1
    ).save()

    TopicDetails.objects.create(
        levelId=1,
        classId=1,
        topicId=2
    ).save()

    TopicDetails.objects.create(
        levelId=1,
        classId=1,
        topicId=3
    ).save()

    TopicDetails.objects.create(
        levelId=1,
        classId=2,
        topicId=1
    ).save()

    TopicDetails.objects.create(
        levelId=1,
        classId=2,
        topicId=2
    ).save()

    TopicDetails.objects.create(
        levelId=1,
        classId=2,
        topicId=3
    ).save()

    TopicDetails.objects.create(
        levelId=1,
        classId=3,
        topicId=1
    ).save()

    TopicDetails.objects.create(
        levelId=1,
        classId=3,
        topicId=2
    ).save()

    TopicDetails.objects.create(
        levelId=1,
        classId=3,
        topicId=3
    ).save()

    TopicDetails.objects.create(
        levelId=1,
        classId=3,
        topicId=4
    ).save()

    TopicDetails.objects.create(
        levelId=2,
        classId=1,
        topicId=1
    ).save()

    TopicDetails.objects.create(
        levelId=2,
        classId=1,
        topicId=2
    ).save()


def pushProgressData(user):
    curriculum = Curriculum.objects.create(
        quizId=4,
        levelId=1,
        classId=3,
        topicId=1,
        quizType='Classwork',
        quizName='1stClasswork')
    Progress.objects.create(user=user, quiz=curriculum, score=100, time='1:00', quizPass=True).save()

    curriculum = Curriculum.objects.create(
        quizId=5,
        levelId=1,
        classId=3,
        topicId=1,
        quizType='HomeWork',
        quizName='131HomeWork')

    Progress.objects.create(user=user, quiz=curriculum, score=90, time='0:40', quizPass=True).save()

    curriculum = Curriculum.objects.create(
        quizId=6,
        levelId=1,
        classId=3,
        topicId=2,
        quizType='Classwork',
        quizName='132Classwork')

    Progress.objects.create(user=user, quiz=curriculum, score=80, time='1:20', quizPass=True).save()

    curriculum = Curriculum.objects.create(
        quizId=7,
        levelId=1,
        classId=3,
        topicId=2,
        quizType='HomeWork',
        quizName='132HomeWork')

    Progress.objects.create(user=user, quiz=curriculum, score=80, time='1:20', quizPass=True).save()

    curriculum = Curriculum.objects.create(
        quizId=8,
        levelId=1,
        classId=3,
        topicId=3,
        quizType='Classwork',
        quizName='133Classwork')

    Progress.objects.create(user=user, quiz=curriculum, score=80, time='1:20', quizPass=True).save()

    curriculum = Curriculum.objects.create(
        quizId=9,
        levelId=1,
        classId=3,
        topicId=3,
        quizType='HomeWork',
        quizName='133HomeWork')

    Progress.objects.create(user=user, quiz=curriculum, score=80, time='1:20', quizPass=True).save()

    curriculum = Curriculum.objects.create(
        quizId=10,
        levelId=1,
        classId=3,
        topicId=4,
        quizType='Classwork',
        quizName='134Classwork')

    Progress.objects.create(user=user, quiz=curriculum, score=80, time='1:20', quizPass=True).save()

    curriculum = Curriculum.objects.create(
        quizId=11,
        levelId=1,
        classId=3,
        topicId=4,
        quizType='HomeWork',
        quizName='134HomeWork')

    Progress.objects.create(user=user, quiz=curriculum, score=80, time='1:20', quizPass=True).save()

    print("EntryComplete!!!!!!!!!!!!!!!")


class TopicsData(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        pushTopicsData()
        print(request)
        data = request.data
        requestLevelId = data['levelId']
        topicDetails = TopicDetails.objects.filter(levelId=requestLevelId)
        topicDetailsDictionary = {}
        for topic in topicDetails:
            try:
                topicDetailsDictionary[topic.classId].append(topic.topicId)
            except:
                topicDetailsDictionary[topic.classId] = [topic.topicId]
        response = Response()
        classData = []
        for i in topicDetailsDictionary:
            classData.append({'classId': i, 'topicIds': topicDetailsDictionary[i]})
            # data()

        requestUserToken = request.headers['AUTH-TOKEN']
        try:
            requestUserId = IdExtraction(requestUserToken)
        except Exception as e:
            return Response({"error": repr(e)}, status=status.HTTP_403_FORBIDDEN)
        userBatchDetails = Student.objects.filter(user=requestUserId).values().first()
        userBatchId = userBatchDetails['batch_id']
        userBatch = Batch.objects.filter(batchId=userBatchId).values().first()
        latestLevel = userBatch['latestLevelId']
        latestClass = userBatch['latestClass_id']

        progressData = []
        if requestLevelId <= 0 or requestLevelId>10:
            return Response({"error": "Level not accessible."}, status=status.HTTP_403_FORBIDDEN)
        elif latestLevel > requestLevelId:
            isLatestLevel = False
        elif latestLevel == requestLevelId:
            isLatestLevel = True
            curriculumDetails = Curriculum.objects.filter(levelId=latestLevel, classId=latestClass)
            for quiz in curriculumDetails:
                quizId = quiz.quizId
                progress = Progress.objects.filter(quiz_id=quizId, user_id=requestUserId).values().first()
                progressData.append(
                    {'topicId': quiz.topicId, 'QuizType': quiz.quizType, 'isPass': progress['quizPass']})
        else:
            return Response({"error": "Level not accessible."}, status=status.HTTP_403_FORBIDDEN)
        response.data = {"schema": classData, "isLatestLevel": isLatestLevel, "progress": progressData}
        return response
#
# class QuizQuestionsData(APIView):
#     permission_classes = [AllowAny]
#
#     def get(self, request):
#         requestLevelId = request['levelId']
#         requestClassId = request['classId']
#         requestQuizType = request['quizType']
#         if requestQuizType == 'test':
#             curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
#                                                           classId=requestClassId,
#                                                           quizType=requestQuizType)
#         else:
#             requestTopicId = request['topicId']
#             curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
#                                                           classId=requestClassId,
#                                                           topicId=requestTopicId,
#                                                           quizType=requestQuizType)
#         requestQuizId = curriculumDetails.first()['quizId']
#         questions = QuizQuestions.objects.filter(quizId=requestQuizId)
#         quizQuestionsSerializer = QuizQuestionsSerializer(questions, many=True)
#         return Response(quizQuestionsSerializer.data)
#
#
# class ProgressUpdate(APIView):
#     def post(self, request):
#         try:
#             idToken = request.headers['AUTH-TOKEN']
#             if idToken is None:
#                 return Response({'expired': "tokenExpired"})
#             requestUserId = IdExtraction(idToken)
#             user = UserDetails.objects.filter(userId=requestUserId)
#             requestQuizId = request['quizId']
#             curriculum = Curriculum.objects.filter(quizId=requestQuizId)
#             requestScore = request['score']
#             requestQuizTime = request['time']
#             requestResult = request['result']
#             progress = Progress.objects.filter(user=user, quiz=curriculum).first()
#             progress.score = requestScore
#             progress.time = requestQuizTime
#             progress.quizPass = requestResult
#             progress.save()
#
#         except Exception as e:
#             Response({"Error Message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#         return Response({'message': 'UpdateSuccessful'})
#
# @method_decorator(ensure_csrf_cookie, name='dispatch')
# class GetCSRFToken(APIView):
#     permission_classes = (permissions.AllowAny)
#
#     def get(self, request, format=None):
#         return Response({'success': 'CSRF cookie set'})

# Create your views here.
