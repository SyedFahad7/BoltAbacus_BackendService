import datetime
import jwt
import json

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.mail import EmailMessage, get_connection
from django.template import loader

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
        if user.exists():
            user = user.first()
            user_password = user['encryptedPassword']
            if password == user_password:
                payload = {
                    "UserId": user["userId"],
                    "expiryTime": str(datetime.datetime.utcnow() + datetime.timedelta(minutes=60)),
                    "creationTime": str(datetime.datetime.utcnow())
                }
                secretKey = "BoltAbacus"
                loginToken = jwt.encode(payload, secretKey, algorithm='HS256')
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
            return Response({"Error Message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        levelId=1,
        classId=4,
        topicId=1
    ).save()

    TopicDetails.objects.create(
        levelId=1,
        classId=4,
        topicId=2
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
        try:
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
            if requestLevelId <= 0 or requestLevelId > 10:
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
            response.data = {"schema": classData, "isLatestLevel": isLatestLevel, "progress": progressData,
                             "latestClass": latestClass}
            return response
        except Exception as e:
            return Response({"Error Message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def pushQuestions():
    QuizQuestions.objects.all().delete()
    curriculum = Curriculum.objects.filter(quizId=4).first()
    QuizQuestions.objects.create(
        questionId=1,
        question="{\"operator\":\"+\",\"numbers\":[1,2,3,4,5,6]}",
        correctAnswer="21",
        quiz=curriculum
    )

    QuizQuestions.objects.create(
        questionId=2,
        question="{\"operator\":\"+\",\"numbers\":[21,-10,-3,140,53,1644]}",
        correctAnswer="21",
        quiz=curriculum
    )

    QuizQuestions.objects.create(
        questionId=3,
        question="{\"operator\":\"/\",\"numbers\":[121,11]}",
        correctAnswer="21",
        quiz=curriculum
    )

    QuizQuestions.objects.create(
        questionId=4,
        question="{\"operator\":\"*\",\"numbers\":[121,11]}",
        correctAnswer="21",
        quiz=curriculum
    )


class QuizQuestionsData(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # pushQuestions()
        try:
            requestUserToken = request.headers['AUTH-TOKEN']
            try:
                requestUserId = IdExtraction(requestUserToken)
            except Exception as e:
                return Response({"error": repr(e)}, status=status.HTTP_403_FORBIDDEN)
            userBatchDetails = Student.objects.filter(user=requestUserId).first()
            userBatchId = userBatchDetails.batch_id
            userBatch = Batch.objects.filter(batchId=userBatchId).first()
            latestLevel = userBatch.latestLevelId
            latestClass = userBatch.latestClass_id

            data = request.data
            requestLevelId = data['levelId']
            requestClassId = data['classId']
            requestQuizType = data['quizType']

            if requestClassId > latestClass:
                return Response({"error": "Quiz not accessible"}, status=status.HTTP_403_FORBIDDEN)

            if requestLevelId > latestLevel:
                return Response({"error": "Quiz not accessible"}, status=status.HTTP_403_FORBIDDEN)

            if requestQuizType == 'Test':
                curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
                                                              classId=requestClassId,
                                                              quizType=requestQuizType).first()
            else:
                requestTopicId = data['topicId']
                curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
                                                              classId=requestClassId,
                                                              topicId=requestTopicId,
                                                              quizType=requestQuizType).first()
            requestQuizId = curriculumDetails.quizId
            questions = QuizQuestions.objects.filter(quiz_id=requestQuizId)
            questionList = []
            for question in questions:
                questionFormat = json.loads(question.question)
                questionList.append({"questionId": question.questionId, "question": questionFormat})
            response = Response()
            response.data = {"questions": questionList, "time": 10, "quizId": requestQuizId}

            return response
        except Exception as e:
            return Response({"Error Message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def ConvertToString(questionJson):
    numbers = questionJson['numbers']
    operator = questionJson['operator']
    if operator == '*' or operator == '/':
        return str(numbers[0]) + operator + str(numbers[1])
    else:
        question = str(numbers[0])
        for i in range(1, len(numbers)):
            if numbers[i] > 0:
                question += (operator + str(numbers[i]))
            else:
                question += str(numbers[i])

        return question


def sendEmail(verdictList, levelId, classId, topicId, quizType, result, emailId):
    content = {
        'levelId': levelId,
        'classId': classId,
        'topicId': topicId,
        'quizType': quizType,
        'verdictList': verdictList,
        'result': result
    }
    template = loader.get_template('EmailTemplate.html').render(content)
    email = EmailMessage(
        ('Report of level ' + str(levelId) + ', class ' + str(classId) + ', topic ' + str(topicId) + ' ' + quizType),
        template,
        'boltabacus.dev@gmail.com',
        [emailId,'boltabacus.dev@gmail.com']
    )
    email.content_subtype = 'html'
    result = email.send()
    return result


class QuizCorrection(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            answers = data['answers']
            verdictList = []
            numberOfCorrectAnswers = 0
            numberOfAnswers = len(answers)
            isPass = False
            for answer in answers:

                questionId = answer['questionId']
                questionObject = QuizQuestions.objects.filter(questionId=questionId).first()
                correctAnswer = questionObject.correctAnswer
                verdict = (float(correctAnswer) == answer['answer'])

                if verdict:
                    numberOfCorrectAnswers += 1
                question = json.loads(questionObject.question)
                questionString = ConvertToString(question)
                verdictList.append({"question": questionString, "verdict": verdict, "answer": answer['answer']})

            if (numberOfCorrectAnswers / numberOfAnswers) >= 0.75:
                isPass = True

            try:
                idToken = request.headers['AUTH-TOKEN']
                if idToken is None:
                    return Response({'expired': "tokenExpired"})
                requestUserId = IdExtraction(idToken)
                user = UserDetails.objects.filter(userId=requestUserId).first()
                requestQuizId = data['quizId']

                curriculum = Curriculum.objects.filter(quizId=requestQuizId).first()
                requestScore = numberOfCorrectAnswers
                requestQuizTime = data['time']

                progress = Progress.objects.filter(user=user, quiz=curriculum).first()
                progress.score = requestScore
                progress.time = requestQuizTime
                progress.quizPass = False
                progress.percentage = (numberOfCorrectAnswers / numberOfAnswers) * 100
                progress.save()

                sendEmail(verdictList,
                          curriculum.levelId,
                          curriculum.classId,
                          curriculum.topicId,
                          curriculum.quizType,
                          isPass,
                          user.email)

                return Response({"results": verdictList, "pass": isPass})
            except Exception as e:
                return Response({"Error Message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"Error Message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReportDetails(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers['AUTH-TOKEN']
            try:
                requestUserId = IdExtraction(requestUserToken)
            except Exception as e:
                return Response({"error": repr(e)}, status=status.HTTP_403_FORBIDDEN)
            data = request.data
            requestLevelId = data['levelId']
            requestClassId = data['classId']

            classQuizDetails = Curriculum.objects.filter(levelId=requestLevelId, classId=requestClassId)
            topicProgress = []
            for quizDetails in classQuizDetails:
                quizId = quizDetails.quizId
                progress = Progress.objects.filter(quiz_id=quizId, user_id=requestUserId).values().first()
                topicProgress.append({"topicId": quizDetails.topicId,
                                      "quizType": quizDetails.quizType,
                                      "percentage": progress['percentage']})
            return Response(topicProgress)
        except Exception as e:
            return Response({"Error Message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Create your views here.
