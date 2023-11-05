import datetime
import random

import jwt
import json
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.mail import EmailMessage
from django.template import loader

from Authentication.models import (UserDetails, Student,
                                   Batch, Curriculum,
                                   TopicDetails, QuizQuestions,
                                   Progress, Teacher)


# ------------ Student Related APIs -----------------------


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
                    "role": user["role"],
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
            latestClass = userBatch['latestClassId']
            return Response({"levelId": latestLevel, "latestClass": latestClass, "latestLink": latestLink},
                            status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            classData = (sorted(classData, key=lambda x: x['classId']))
            requestUserToken = request.headers['AUTH-TOKEN']
            try:
                requestUserId = IdExtraction(requestUserToken)
            except Exception as e:
                return Response({"error": repr(e)}, status=status.HTTP_403_FORBIDDEN)
            userBatchDetails = Student.objects.filter(user=requestUserId).values().first()
            userBatchId = userBatchDetails['batch_id']
            userBatch = Batch.objects.filter(batchId=userBatchId).values().first()
            latestLevel = userBatch['latestLevelId']
            latestClass = userBatch['latestClassId']

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
                        {'topicId': quiz.topicId,
                         'QuizType': quiz.quizType,
                         'isPass': progress['quizPass'],
                         'percentage': progress['percentage']})
            else:
                return Response({"error": "Level not accessible."}, status=status.HTTP_403_FORBIDDEN)
            response.data = {"schema": classData, "isLatestLevel": isLatestLevel, "progress": progressData,
                             "latestClass": latestClass}
            return response
        except Exception as e:
            return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            latestClass = userBatch.latestClassId

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
            return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
                progress.quizPass = isPass
                progress.percentage = (numberOfCorrectAnswers / numberOfAnswers) * 100
                progress.save()

                sendEmail(verdictList,
                          curriculum.levelId,
                          curriculum.classId,
                          curriculum.topicId,
                          curriculum.quizType,
                          isPass,
                          user.email)

                return Response({"results": verdictList, "pass": isPass, "time": requestQuizTime})
            except Exception as e:
                return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            userBatchDetails = Student.objects.filter(user=requestUserId).values().first()
            userBatchId = userBatchDetails['batch_id']
            userBatch = Batch.objects.filter(batchId=userBatchId).values().first()
            latestLevel = userBatch['latestLevelId']
            latestClass = userBatch['latestClassId']
            if requestLevelId > latestLevel or (requestClassId > latestClass and requestLevelId == latestLevel):
                return Response({"message": "Report not accessible."}, status=status.HTTP_403_FORBIDDEN)
            classQuizDetails = Curriculum.objects.filter(levelId=requestLevelId, classId=requestClassId)
            topicProgress = {}
            for quizDetails in classQuizDetails:
                quizId = quizDetails.quizId
                progress = Progress.objects.filter(quiz_id=quizId, user_id=requestUserId).values().first()
                try:
                    topicProgress[quizDetails.topicId].update({quizDetails.quizType: progress['percentage']})
                except:
                    topicProgress[quizDetails.topicId] = {quizDetails.quizType: progress['percentage']}
            progressOfTopics = []
            for topicResult in topicProgress:
                result = topicProgress[topicResult]
                if topicResult != 0:
                    progressOfTopics.append({"topicId": topicResult,
                                             "Classwork": result['Classwork'],
                                             "Homework": result['Homework']})
            test = {"Test": topicProgress[0]['Test']}
            return Response({"quiz": progressOfTopics, "test": test})
        except Exception as e:
            return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class data(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # pushProgressData()
        # pushTopicsData()
        # pushQuestions()
        # addAdminUser()
        return Response("message")


def addAdminUser():
    adminUser = UserDetails.objects.create(
        firstName="Bolt",
        lastName="Abacus",
        phoneNumber="+919032024912",
        email="boltabacus.dev@gmail.com",
        role="Admin",
        encryptedPassword="password1",
        created_date=datetime.datetime.now(),
        blocked=False
    )
    adminUser.save()


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
        [emailId, 'boltabacus.dev@gmail.com']
    )
    email.content_subtype = 'html'
    result = email.send()
    return result


def IdExtraction(token):
    try:
        secretKey = "BoltAbacus"
        payload = jwt.decode(token, secretKey, algorithms=['HS256'])
        userId = payload['UserId']
        return userId
    except Exception as e:
        return e


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


def pushProgressData():
    UserDetails.objects.all().delete()
    user = UserDetails.objects.create(
        userId=1,
        firstName='anish',
        lastName='U',
        phoneNumber='9635404926',
        email='anishu@gmail.com',
        role='Student',
        encryptedPassword='password1',
        created_date='2023-09-30',
        blocked=0
    )
    user.save()
    user = UserDetails.objects.filter(firstName='anish').first()
    Student.objects.all().delete()
    Batch.objects.all().delete()
    Progress.objects.all().delete()
    Curriculum.objects.all().delete()
    curriculum = Curriculum.objects.create(
        quizId=4,
        levelId=1,
        classId=3,
        topicId=1,
        quizType='Classwork',
        quizName='1stClasswork')
    Progress.objects.create(user=user, quiz=curriculum, score=100, time='100', quizPass=True).save()
    curriculum = Curriculum.objects.create(
        quizId=3,
        levelId=1,
        classId=3,
        topicId=0,
        quizType='Test',
        quizName='130Test')
    Progress.objects.create(user=user, quiz=curriculum, score=100, time='100', quizPass=True).save()

    batch = Batch.objects.create(
        batchId=2,
        timeDay='Wednesday',
        timeSchedule='10:00AM',
        numberOfStudents=2,
        active=1,
        batchName='FirstBatch',
        latestLevelId=1,
        latestClassId=3,
        latestLink='www.google.com')
    userStudentEntry = Student.objects.create(user=user, batch=batch)

    curriculum = Curriculum.objects.create(
        quizId=5,
        levelId=1,
        classId=3,
        topicId=1,
        quizType='Homework',
        quizName='131Homework')

    Progress.objects.create(user=user, quiz=curriculum, score=90, time='40', quizPass=True).save()

    curriculum = Curriculum.objects.create(
        quizId=6,
        levelId=1,
        classId=3,
        topicId=2,
        quizType='Classwork',
        quizName='132Classwork')

    Progress.objects.create(user=user, quiz=curriculum, score=80, time='120', quizPass=True).save()

    curriculum = Curriculum.objects.create(
        quizId=7,
        levelId=1,
        classId=3,
        topicId=2,
        quizType='Homework',
        quizName='132Homework')

    Progress.objects.create(user=user, quiz=curriculum, score=80, time='120', quizPass=True).save()

    curriculum = Curriculum.objects.create(
        quizId=8,
        levelId=1,
        classId=3,
        topicId=3,
        quizType='Classwork',
        quizName='133Classwork')

    Progress.objects.create(user=user, quiz=curriculum, score=80, time='120', quizPass=True).save()

    curriculum = Curriculum.objects.create(
        quizId=9,
        levelId=1,
        classId=3,
        topicId=3,
        quizType='Homework',
        quizName='133Homework')

    Progress.objects.create(user=user, quiz=curriculum, score=80, time='120', quizPass=True).save()

    curriculum = Curriculum.objects.create(
        quizId=10,
        levelId=1,
        classId=3,
        topicId=4,
        quizType='Classwork',
        quizName='134Classwork')

    Progress.objects.create(user=user, quiz=curriculum, score=80, time='120', quizPass=True).save()

    curriculum = Curriculum.objects.create(
        quizId=11,
        levelId=1,
        classId=3,
        topicId=4,
        quizType='Homework',
        quizName='134Homework')

    Progress.objects.create(user=user, quiz=curriculum, score=80, time='120', quizPass=True).save()

    print("EntryComplete!!!!!!!!!!!!!!!")


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


# -------------------- Admin Related APIs ----------------------

class getAllQuestions(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data

            requestLevelId = data['levelId']
            requestClassId = data['classId']
            requestQuizType = data['quizType']
            requestTopicId = data['topicId']

            if requestQuizType == 'Test':
                curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
                                                              classId=requestClassId,
                                                              quizType=requestQuizType).first()
            else:
                curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
                                                              classId=requestClassId,
                                                              topicId=requestTopicId,
                                                              quizType=requestQuizType).first()
            if curriculumDetails is None:
                return Response({"message": "Quiz doesn't exist"}, status=status.HTTP_403_FORBIDDEN)
            quizId = curriculumDetails.quizId
            questions = QuizQuestions.objects.filter(quiz_id=quizId)
            questionList = []
            for question in questions:
                questionFormat = json.loads(question.question)
                questionList.append({"questionId": question.questionId, "question": questionFormat,
                                     "correctAnswer": int(question.correctAnswer)})
            response = Response()
            response.data = {"questions": questionList, "time": 10, "quizId": quizId}

            return response
        except Exception as e:
            return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EditQuestion(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            questionId = data['questionId']
            question = data['question']
            correctAnswer = data['correctAnswer']
            questionFromDb = QuizQuestions.objects.filter(questionId=questionId).first()
            questionFormat = json.dumps(question)
            questionFromDb.question = questionFormat
            questionFromDb.correctAnswer = correctAnswer
            questionFromDb.save()
            return Response({"message": "Success"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetQuestion(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            questionId = data['questionId']
            questionFromDb = QuizQuestions.objects.filter(questionId=questionId).first()
            questionFormat = json.loads(questionFromDb.question)
            return Response({"questionId": questionId,
                             "question": questionFormat,
                             "correctAnswer": int(questionFromDb.correctAnswer)}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddQuestion(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            questionJson = data['question']
            correctAnswer = data['correctAnswer']
            requestLevelId = data['levelId']
            requestClassId = data['classId']
            requestQuizType = data['quizType']
            requestTopicId = data['topicId']
            if requestQuizType == 'Test':
                curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
                                                              classId=requestClassId,
                                                              quizType=requestQuizType).first()
            else:
                curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
                                                              classId=requestClassId,
                                                              topicId=requestTopicId,
                                                              quizType=requestQuizType).first()
            if curriculumDetails is None:
                return Response({"message": "Quiz doesn't exist"}, status=status.HTTP_403_FORBIDDEN)
            quizId = curriculumDetails.quizId
            questionString = json.dumps(questionJson)
            questionDetails = QuizQuestions.objects.create(question=questionString,
                                                           quiz_id=quizId,
                                                           correctAnswer=correctAnswer)
            questionDetails.save()
            return Response({"message": "Success"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetAllBatches(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        batchIdDetails = Batch.objects.all().values()
        batchIds = []
        for batchId in batchIdDetails:
            batchIds.append({"batchId": batchId['batchId'], "batchName": batchId['batchName']})
        return Response({"batches": batchIds})


class AddBatch(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            timeDay = data['timeDay']
            timeSchedule = data['timeSchedule']
            batchName = data['batchName']
            teacherUserId = data['userId']
            user = UserDetails.objects.filter(userId=teacherUserId).first()
            if user.role != "Teacher":
                return Response({"message": "Given User is not a Teacher"}, status=status.HTTP_403_FORBIDDEN)
            else:
                newBatch = Batch.objects.create(
                    timeDay=timeDay,
                    timeSchedule=timeSchedule,
                    numberOfStudents=0,
                    active=True,
                    batchName=batchName,
                    latestLevelId=1,
                    latestClassId=1
                )

                teacher = Teacher.objects.create(
                    user_id=teacherUserId,
                    batchId=newBatch.batchId
                )
                teacher.save()
                newBatch.save()
                return Response({"message": "Success"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetBatch(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            batchId = data['batchId']
            batchDetails = Batch.objects.filter(batchId=batchId).first()
            return Response({
                "batchId": batchDetails.batchId,
                "timeDay": batchDetails.timeDay,
                "timeSchedule": batchDetails.timeSchedule,
                "numberOfStudents": batchDetails.numberOfStudents,
                "active": batchDetails.active,
                "batchName": batchDetails.batchName,
                "latestLevelId": batchDetails.latestLevelId,
                "latestClassId": batchDetails.latestClassId
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EditBatchDetails(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            batchId = data['batchId']
            timeDay = data['timeDay']
            timeSchedule = data['timeSchedule']
            batchName = data['batchName']
            numberOfStudents = data['numberOfStudents']
            active = data['active']
            latestLevelId = data['latestLevelId']
            latestClassId = data['latestClassId']
            batchDetails = Batch.objects.filter(batchId=batchId).first()
            batchDetails.timeDay = timeDay
            batchDetails.timeSchedule = timeSchedule
            batchDetails.batchName = batchName
            batchDetails.numberOfStudents = numberOfStudents
            batchDetails.active = active
            batchDetails.latestLevelId = latestLevelId
            batchDetails.latestClassId = latestClassId
            batchDetails.save()
            return Response({"message": "Success"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteBatch(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            batchId = data['batchId']
            batchStudents = Student.objects.filter(batch_id=batchId).first()
            if batchStudents:
                return Response({"message": "Cannot Delete the batch as it has students in it"},
                                status=status.HTTP_403_FORBIDDEN)
            batchDetails = Batch.objects.filter(batchId=batchId).first()
            batchDetails.delete()
            return Response({"message": "Success"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddTeacher(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            password = generatePassword()
            firstName = data['firstName']
            lastName = data['lastName']
            phoneNumber = data['phoneNumber']
            email = data['email']
            if UserDetails.objects.filter(email=email).first() != None:
                return Response({"message": "User with this email already Exists"}, status=status.HTTP_400_BAD_REQUEST)
            user = UserDetails.objects.create(
                firstName=firstName,
                lastName=lastName,
                phoneNumber=phoneNumber,
                email=email,
                role="Teacher",
                encryptedPassword=encryptPassword(password),
                created_date=datetime.datetime.now(),
                blocked=False
            )
            user.save()
            email = EmailMessage(
                'Account has been Created',
                "An account has been created for this email id for the teacher role. The password is " + password + ". Please login and change your password",
                'boltabacus.dev@gmail.com',
                [email, 'boltabacus.dev@gmail.com']
            )
            email.send()

            return Response({"message": "Success"},
                            status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": repr(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetTeachers(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:

            teacherDetails = UserDetails.objects.filter(role="Teacher")
            teachers = []
            for teacher in teacherDetails:
                teachers.append({"userId": teacher.userId,
                                 "firstName": teacher.firstName,
                                 "lastName": teacher.lastName})
            return Response({"teachers": teachers}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# class AssignBatch(APIView):
#     permission_classes = [AllowAny]
#
#     def post(self, request):
#         try:
#             data = request.data
#             teacherId = data['userId']
#             teacher = UserDetails.objects.filter(userId=teacherId).first()
#             if teacher:
#                 if teacher.role == "Teacher":
#                     batchId = data['batchId']
#                     return assignUserToBatch(Teacher, batchId, teacherId, "Teacher")
#                 else:
#                     return Response({"message": "Given user is not a teacher"},
#                                     status=status.HTTP_403_FORBIDDEN)
#             else:
#                 return Response({"message": "Given user doesn't exist"},
#                                 status=status.HTTP_403_FORBIDDEN)
#         except Exception as e:
#             return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# class AssignStudentToBatch(APIView):
#     permission_classes = [AllowAny]
#
#     def post(self, request):
#         try:
#             data = request.data
#             studentId = data['userId']
#             student = UserDetails.objects.filter(userId=studentId).first()
#             if student:
#                 if student.role == "Student":
#                     batchId = data['batchId']
#                     return assignUserToBatch(Student, batchId, studentId, "Student")
#                 else:
#                     return Response({"message": "Given user is not a Student"},
#                                     status=status.HTTP_403_FORBIDDEN)
#
#             else:
#                 return Response({"message": "Given user doesn't exist"},
#                                 status=status.HTTP_403_FORBIDDEN)
#
#             pass
#         except Exception as e:
#             return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddStudent(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return createUser(request, Student, "Student")


class GetStudents(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            batchId = request.data['batchId']
            StudentList = getStudentIds(batchId)
            students = []

            for i in StudentList:
                student = UserDetails.objects.filter(userId=i).first()
                students.append({"userId": student.userId,
                                 "firstName": student.firstName,
                                 "lastName": student.lastName})
            return Response({"students": students}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetTopicsData(APIView):
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
            classData = []
            for i in topicDetailsDictionary:
                classData.append({'classId': i, 'topicIds': topicDetailsDictionary[i]})
            classData = (sorted(classData, key=lambda x: x['classId']))
            return Response({"schema": classData}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": repr(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def getStudentIds(batchId):
    studentIdDetails = Student.objects.filter(batch_id=batchId).values("user_id")
    studentIds = []
    for studentId in studentIdDetails:
        studentIds.append(studentId['user_id'])
    return studentIds


def getBatchList():
    batchIdDetails = Batch.objects.all().values("batchId")
    batchIds = []
    for batchId in batchIdDetails:
        batchIds.append(batchId['batchId'])
    return batchIds


def createUser(request, dbObject, role):
    try:
        data = request.data

        firstName = data['firstName']
        lastName = data['lastName']
        phoneNumber = data['phoneNumber']
        email = data['email']
        if UserDetails.objects.filter(email=email).first() != None:
            return Response({"message": "User with this email already Exists"}, status=status.HTTP_400_BAD_REQUEST)

        password = generatePassword()

        batchId = data['batchId']
        batchList = getBatchList()
        if batchId in batchList:
            user = UserDetails.objects.create(
                firstName=firstName,
                lastName=lastName,
                phoneNumber=phoneNumber,
                email=email,
                role=role,
                encryptedPassword=encryptPassword(password),
                created_date=datetime.datetime.now(),
                blocked=False
            )
            user.save()

            roleRelatedObject = dbObject.objects.create(
                user=user,
                batch_id=batchId
            )
            roleRelatedObject.save()

            if role == "Student":
                batchDetails = Batch.objects.filter(batchId=batchId).first()
                latestLevel = batchDetails.latestLevelId
                latestClass = batchDetails.latestClassId
                for i in range(latestLevel + 1):
                    classes = getClassIds(i)
                    for j in classes:
                        curriculum = Curriculum.objects.filter(levelId=i, classId=j)
                        for quiz in curriculum:
                            if (quiz.levelId < latestLevel) or (quiz.classId <= latestClass and
                                                                quiz.levelId == latestLevel):
                                progress = Progress.objects.create(
                                    quiz_id=quiz.quizId,
                                    user_id=user.userId
                                )
                                progress.save()

                            else:
                                break

            email = EmailMessage(
                'Account has been Created',
                "An account has been created for this email id for the teacher role. The password is " + password + ". Please login and change your password",
                'boltabacus.dev@gmail.com',
                [email, 'boltabacus.dev@gmail.com']
            )
            email.send()
            return Response({"message": "Success"},
                            status=status.HTTP_200_OK)
        else:
            return Response({"message": "Given batch Id is invalid"},
                            status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        return Response({"message": repr(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# def assignUserToBatch(dbObject, batchId, userId, role):
#     batchList = getBatchList()
#     if batchId in batchList:
#         try:
#             dbObjectInstance = dbObject.objects.filter(
#                 user_id=userId
#             ).first()
#             if role == "Teacher":
#                 previousbatchId = dbObjectInstance.batchId
#                 dbObjectInstance.batchId = batchId
#             else:
#                 previousbatchId = dbObjectInstance.batch_id
#                 dbObjectInstance.batch_id = batchId
#             dbObjectInstance.save()
#             if role == "Student":
#                 addProgressIfNeeded(previousbatchId, batchId, userId)
#             return Response({"message": "Success"},
#                             status=status.HTTP_200_OK)
#         except Exception as e:
#             return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#     else:
#
#         return Response({"message": "Given batch Id is invalid"},
#                         status=status.HTTP_403_FORBIDDEN)
#
#
# def addProgressIfNeeded(previousBatchId, currentBatchId, userId):
#     previousBatch = Batch.objects.filter(batchId=previousBatchId).first()
#     currentBatch = Batch.objects.filter(batchId=currentBatchId).first()
#     previousLatestLevel = previousBatch.latestLevelId
#     currentLatestLevel = currentBatch.latestLevelId
#     previousLatestClass = previousBatch.latestClassId
#     currentLatestClass = currentBatch.latestClassId
#     if ((currentLatestLevel > previousLatestLevel) or
#             (currentLatestLevel == previousLatestLevel and previousLatestClass < currentLatestClass)):
#         for i in range(previousLatestLevel, currentLatestLevel +1):
#             curriculum = Curriculum.objects.filter(levelId=i)
#             for quiz in curriculum:
#                 if ((quiz.levelId < currentLatestLevel) or
#                         (quiz.classId <= currentLatestClass and
#                          quiz.levelId == currentLatestLevel)):
#                     if not Progress.objects.filter(quiz_id=quiz.quizId, user_id=userId).first():
#                         progress = Progress.objects.create(
#                             quiz_id=quiz.quizId,
#                             user_id=userId
#                         )
#                         progress.save()
#                 else:
#                     break


def encryptPassword(password):
    return password


def generatePassword():
    n = random.randint(10, 15)
    characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ123456789"

    password = ""

    for i in range(n):
        password += random.choice(characters)

    return password


# ------ Teacher related APIs ------


class UpdateBatchLink(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            batchId = data["batchId"]
            link = data["link"]
            batch = Batch.objects.filter(batchId=batchId).first()
            if batch is None:
                return Response({"message": "Batch doesn't exist."}, status=status.HTTP_403_FORBIDDEN)
            batch.latestLink = link
            batch.save()
            return Response({"message": "Success"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetTeacherBatches(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            requestUserToken = request.headers['AUTH-TOKEN']
            try:
                userId = IdExtraction(requestUserToken)
            except Exception as e:
                return Response({"error": repr(e)}, status=status.HTTP_403_FORBIDDEN)
            user = UserDetails.objects.filter(userId=userId).first()
            if user is None:
                return Response({"message": "User doesn't exist."}, status=status.HTTP_403_FORBIDDEN)
            else:
                if user.role != "Teacher":
                    return Response({"message": "User is not a Teacher"}, status=status.HTTP_403_FORBIDDEN)

            teacher = Teacher.objects.filter(user_id=userId)
            batches = {
                "Monday": [],
                "Tuesday": [],
                "Wednesday": [],
                "Thursday": [],
                "Friday": [],
                "Saturday": [],
                "Sunday": [],
            }
            for teacherBatch in teacher:
                batchId = teacherBatch.batchId
                batch = Batch.objects.filter(batchId=batchId).first()
                batches[batch.timeDay].append(
                    {"batchId": batch.batchId, "batchName": batch.batchName, "timings": batch.timeSchedule})
            return Response({"batches": batches})
        except Exception as e:
            return Response({"message": repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def getClassIds(levelId):
    classIds=set()
    classes = TopicDetails.objects.filter(levelId=levelId)
    for eachClass in classes:
        classIds.add(eachClass.classId)
    return classIds
# Create your views here.
