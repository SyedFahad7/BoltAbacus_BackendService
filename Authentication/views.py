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
from . import Constants
from Authentication.models import (UserDetails, Student,
                                   Batch, Curriculum,
                                   TopicDetails, QuizQuestions,
                                   Progress, Teacher, OrganizationTag)


# ------------ Student Related APIs -----------------------


class SignIn(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        data = self.request.data
        email = data[Constants.EMAIL]
        email = email.lower()
        password = data[Constants.PASSWORD]
        user = UserDetails.objects.filter(email=email).values()
        if user.exists():
            user = user.first()
            user_password = user[Constants.ENCRYPTED_PASSWORD]
            if password == user_password:
                organization = OrganizationTag.objects.filter(tagId=user["tag_id"]).first()
                organizationExpirationDate = organization.expirationDate
                if organizationExpirationDate < datetime.date.today():
                    return Response({Constants.JSON_MESSAGE: "The subscription has expired. Please contact the "
                                                             "administrator to renew it."},
                                    status=status.HTTP_403_FORBIDDEN)
                payload = {
                    Constants.USER_ID: user[Constants.USER_ID],
                    Constants.ROLE: user[Constants.ROLE],
                    Constants.EXPIRY_TIME: str(datetime.datetime.utcnow() + datetime.timedelta(minutes=60)),
                    "creationTime": str(datetime.datetime.utcnow()),
                    Constants.ORGANIZATION_EXPIRATION_DATE: str(organizationExpirationDate)
                }
                secretKey = Constants.SECRET_KEY
                loginToken = jwt.encode(payload, secretKey, algorithm='HS256')
                response = Response({
                    Constants.EMAIL: user[Constants.EMAIL],
                    Constants.ROLE: user[Constants.ROLE],
                    Constants.FIRST_NAME: user[Constants.FIRST_NAME],
                    Constants.LAST_NAME: user[Constants.LAST_NAME],
                    "phone": user[Constants.PHONE_NUMBER],
                    Constants.ORGANIZATION_NAME: organization.organizationName,
                    "token": loginToken
                },
                    status=status.HTTP_200_OK
                )
                return response
            else:
                return Response({Constants.JSON_MESSAGE: "Invalid Password. Try Again"},
                                status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({Constants.JSON_MESSAGE: "Invalid Credentials. Try Again"},
                            status=status.HTTP_401_UNAUTHORIZED)


class CurrentLevels(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            idToken = request.headers[Constants.TOKEN_HEADER]
            if idToken is None:
                return Response({Constants.JSON_MESSAGE: "tokenExpired"})
            secretKey = Constants.SECRET_KEY
            payload = jwt.decode(idToken, secretKey, algorithms=['HS256'])
            userId = payload[Constants.USER_ID]
            userBatchDetails = Student.objects.filter(user=userId).values().first()
            userBatchId = userBatchDetails['batch_id']
            userBatch = Batch.objects.filter(batchId=userBatchId).values().first()
            latestLevel = userBatch[Constants.LATEST_LEVEL_ID]
            latestLink = userBatch[Constants.LATEST_LINK]
            latestClass = userBatch[Constants.LATEST_CLASS_ID]
            return Response({Constants.LEVEL_ID: latestLevel, Constants.LATEST_CLASS: latestClass,
                             Constants.LATEST_LINK: latestLink},
                            status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TopicsData(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            requestLevelId = data[Constants.LEVEL_ID]
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
                classData.append({Constants.CLASS_ID: i, 'topicIds': topicDetailsDictionary[i]})
            classData = (sorted(classData, key=lambda x: x[Constants.CLASS_ID]))
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                requestUserId = IdExtraction(requestUserToken)
                if isinstance(requestUserId, Exception):
                    raise Exception(requestUserToken)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            userBatchDetails = Student.objects.filter(user=requestUserId).values().first()
            userBatchId = userBatchDetails['batch_id']
            userBatch = Batch.objects.filter(batchId=userBatchId).values().first()
            latestLevel = userBatch[Constants.LATEST_LEVEL_ID]
            latestClass = userBatch[Constants.LATEST_CLASS_ID]

            progressData = []
            if requestLevelId <= 0 or requestLevelId > 10:
                return Response({Constants.JSON_MESSAGE: "Level not accessible."}, status=status.HTTP_403_FORBIDDEN)
            elif latestLevel > requestLevelId:
                isLatestLevel = False
            elif latestLevel == requestLevelId:
                isLatestLevel = True
                curriculumDetails = Curriculum.objects.filter(levelId=latestLevel, classId=latestClass)
                for quiz in curriculumDetails:
                    quizId = quiz.quizId
                    progress = Progress.objects.filter(quiz_id=quizId, user_id=requestUserId).values().first()
                    progressData.append(
                        {Constants.TOPIC_ID: quiz.topicId,
                         'QuizType': quiz.quizType,
                         'isPass': progress['quizPass'],
                         Constants.PERCENTAGE: progress[Constants.PERCENTAGE]})
            else:
                return Response({Constants.JSON_MESSAGE: "Level not accessible."}, status=status.HTTP_403_FORBIDDEN)
            response.data = {"schema": classData, "isLatestLevel": isLatestLevel, "progress": progressData,
                             Constants.LATEST_CLASS: latestClass}
            return response
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QuizQuestionsData(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                requestUserId = IdExtraction(requestUserToken)
                if isinstance(requestUserId, Exception):
                    raise Exception(requestUserToken)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            userBatchDetails = Student.objects.filter(user=requestUserId).first()
            userBatchId = userBatchDetails.batch_id
            userBatch = Batch.objects.filter(batchId=userBatchId).first()
            latestLevel = userBatch.latestLevelId
            latestClass = userBatch.latestClassId

            data = request.data
            requestLevelId = data[Constants.LEVEL_ID]
            requestClassId = data[Constants.CLASS_ID]
            requestQuizType = data[Constants.QUIZ_TYPE]

            if requestLevelId > latestLevel and requestClassId > latestClass:
                return Response({Constants.JSON_MESSAGE: "Quiz not accessible"}, status=status.HTTP_403_FORBIDDEN)

            if requestLevelId > latestLevel:
                return Response({Constants.JSON_MESSAGE: "Quiz not accessible"}, status=status.HTTP_403_FORBIDDEN)

            if requestQuizType == Constants.TEST:
                curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
                                                              classId=requestClassId,
                                                              quizType=requestQuizType).first()
            else:
                requestTopicId = data[Constants.TOPIC_ID]
                curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
                                                              classId=requestClassId,
                                                              topicId=requestTopicId,
                                                              quizType=requestQuizType).first()
            requestQuizId = curriculumDetails.quizId
            questions = QuizQuestions.objects.filter(quiz_id=requestQuizId)
            questionList = []
            for question in questions:
                questionFormat = json.loads(question.question)
                questionList.append({Constants.QUESTION_ID: question.questionId, Constants.QUESTION: questionFormat})
            response = Response()
            response.data = {Constants.QUESTIONS: questionList, Constants.TIME: 10, Constants.QUIZ_ID: requestQuizId}

            return response
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

                questionId = answer[Constants.QUESTION_ID]
                questionObject = QuizQuestions.objects.filter(questionId=questionId).first()
                correctAnswer = questionObject.correctAnswer
                verdict = (float(correctAnswer) == answer[Constants.ANSWER])

                if verdict:
                    numberOfCorrectAnswers += 1
                question = json.loads(questionObject.question)
                questionString = ConvertToString(question)
                verdictList.append({Constants.QUESTION: questionString, "verdict": verdict,
                                    Constants.ANSWER: answer[Constants.ANSWER]})
            if (numberOfCorrectAnswers / numberOfAnswers) >= 0.75:
                isPass = True
            try:
                idToken = request.headers[Constants.TOKEN_HEADER]
                if idToken is None:
                    return Response({Constants.JSON_MESSAGE: "tokenExpired"})
                requestUserId = IdExtraction(idToken)
                user = UserDetails.objects.filter(userId=requestUserId).first()
                requestQuizId = data[Constants.QUIZ_ID]

                curriculum = Curriculum.objects.filter(quizId=requestQuizId).first()
                requestScore = numberOfCorrectAnswers
                requestQuizTime = data[Constants.TIME]
                percentage = (numberOfCorrectAnswers / numberOfAnswers) * 100
                progress = Progress.objects.filter(user=user, quiz=curriculum).first()
                progress.score = requestScore
                progress.time = requestQuizTime
                progress.quizPass = isPass
                progress.percentage = percentage
                progress.save()

                sendEmail(verdictList,
                          curriculum.levelId,
                          curriculum.classId,
                          curriculum.topicId,
                          curriculum.quizType,
                          isPass,
                          user.email,
                          percentage,
                          secondsToMinutes(requestQuizTime),
                          requestScore)

                return Response({"results": verdictList, "pass": isPass, Constants.TIME: requestQuizTime})
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReportDetails(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                requestUserId = IdExtraction(requestUserToken)
                if isinstance(requestUserId, Exception):
                    raise Exception(requestUserToken)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            data = request.data
            requestLevelId = data[Constants.LEVEL_ID]
            requestClassId = data[Constants.CLASS_ID]
            userBatchDetails = Student.objects.filter(user=requestUserId).values().first()
            userBatchId = userBatchDetails['batch_id']
            userBatch = Batch.objects.filter(batchId=userBatchId).values().first()
            latestLevel = userBatch[Constants.LATEST_LEVEL_ID]
            latestClass = userBatch[Constants.LATEST_CLASS_ID]
            if requestLevelId > latestLevel or (requestClassId > latestClass and requestLevelId == latestLevel):
                return Response({Constants.JSON_MESSAGE: "Report not accessible."}, status=status.HTTP_403_FORBIDDEN)
            classQuizDetails = Curriculum.objects.filter(levelId=requestLevelId, classId=requestClassId)
            topicProgress = {}
            for quizDetails in classQuizDetails:
                quizId = quizDetails.quizId
                progress = Progress.objects.filter(quiz_id=quizId, user_id=requestUserId).values().first()
                try:
                    topicProgress[quizDetails.topicId].update(
                        {quizDetails.quizType: progress[Constants.PERCENTAGE],
                         quizDetails.quizType + "Time": progress[Constants.TIME]})
                except:
                    topicProgress[quizDetails.topicId] = {quizDetails.quizType: progress[Constants.PERCENTAGE],
                                                          quizDetails.quizType + "Time": progress[Constants.TIME]}
            progressOfTopics = []
            for topicResult in topicProgress:
                result = topicProgress[topicResult]
                if topicResult != 0:
                    progressOfTopics.append({Constants.TOPIC_ID: topicResult,
                                             Constants.CLASSWORK: result[Constants.CLASSWORK],
                                             Constants.CLASSWORK_TIME: result[Constants.CLASSWORK_TIME],
                                             Constants.HOMEWORK: result[Constants.HOMEWORK],
                                             Constants.HOMEWORK_TIME: result[Constants.HOMEWORK_TIME]
                                             })
            test = {Constants.TEST: topicProgress[0][Constants.TEST], "Time": topicProgress[0][Constants.TEST_TIME]}
            return Response({"quiz": progressOfTopics, "test": test})
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class data(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        temp()
        return Response(Constants.JSON_MESSAGE)


class ResetPassword(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                requestUserId = IdExtraction(requestUserToken)
                if isinstance(requestUserId, Exception):
                    raise Exception(requestUserToken)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            data = request.data
            password = data[Constants.PASSWORD]
            user = UserDetails.objects.filter(userId=requestUserId).first()
            user.encryptedPassword = password
            user.save()
            return Response({Constants.JSON_MESSAGE: Constants.SUCCESS_MESSAGE}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def secondsToMinutes(time):
    minutes = time // 60
    seconds = time % 60
    return str(minutes) + " minutes and " + str(seconds) + " seconds"


def sendEmail(verdictList, levelId, classId, topicId, quizType, result, emailId, percentage, time, score):
    content = {
        Constants.LEVEL_ID: levelId,
        Constants.CLASS_ID: classId,
        Constants.TOPIC_ID: topicId,
        Constants.QUIZ_TYPE: quizType,
        'verdictList': verdictList,
        'result': result,
        Constants.TIME: time,
        Constants.PERCENTAGE: percentage,
        'score': score
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
        secretKey = Constants.SECRET_KEY
        payload = jwt.decode(token, secretKey, algorithms=['HS256'])
        userId = payload[Constants.USER_ID]
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


# -------------------- Admin Related APIs ----------------------

class GetAllQuestions(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data

            requestLevelId = data[Constants.LEVEL_ID]
            requestClassId = data[Constants.CLASS_ID]
            requestQuizType = data[Constants.QUIZ_TYPE]
            requestTopicId = data[Constants.TOPIC_ID]

            if requestQuizType == Constants.TEST:
                curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
                                                              classId=requestClassId,
                                                              quizType=requestQuizType).first()
            else:
                curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
                                                              classId=requestClassId,
                                                              topicId=requestTopicId,
                                                              quizType=requestQuizType).first()
            if curriculumDetails is None:
                return Response({Constants.JSON_MESSAGE: "Quiz doesn't exist"}, status=status.HTTP_403_FORBIDDEN)
            quizId = curriculumDetails.quizId
            questions = QuizQuestions.objects.filter(quiz_id=quizId)
            questionList = []
            for question in questions:
                questionFormat = json.loads(question.question)
                questionList.append({Constants.QUESTION_ID: question.questionId, Constants.QUESTION: questionFormat,
                                     Constants.CORRECT_ANSWER: int(question.correctAnswer)})
            response = Response()
            response.data = {Constants.QUESTIONS: questionList, Constants.TIME: 10, Constants.QUIZ_ID: quizId}

            return response
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EditQuestion(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            questionId = data[Constants.QUESTION_ID]
            question = data[Constants.QUESTION]
            correctAnswer = data[Constants.CORRECT_ANSWER]
            questionFromDb = QuizQuestions.objects.filter(questionId=questionId).first()
            questionFormat = json.dumps(question)
            questionFromDb.question = questionFormat
            questionFromDb.correctAnswer = correctAnswer
            questionFromDb.save()
            return Response({Constants.JSON_MESSAGE: Constants.SUCCESS_MESSAGE}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetQuestion(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            questionId = data[Constants.QUESTION_ID]
            questionFromDb = QuizQuestions.objects.filter(questionId=questionId).first()
            questionFormat = json.loads(questionFromDb.question)
            return Response({Constants.QUESTION_ID: questionId,
                             Constants.QUESTION: questionFormat,
                             Constants.CORRECT_ANSWER: int(questionFromDb.correctAnswer)}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddQuestion(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            questionJson = data[Constants.QUESTION]
            correctAnswer = data[Constants.CORRECT_ANSWER]
            requestLevelId = data[Constants.LEVEL_ID]
            requestClassId = data[Constants.CLASS_ID]
            requestQuizType = data[Constants.QUIZ_TYPE]
            requestTopicId = data[Constants.TOPIC_ID]
            if requestQuizType == Constants.TEST:
                curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
                                                              classId=requestClassId,
                                                              quizType=requestQuizType).first()
            else:
                curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
                                                              classId=requestClassId,
                                                              topicId=requestTopicId,
                                                              quizType=requestQuizType).first()
            if curriculumDetails is None:
                return Response({Constants.JSON_MESSAGE: "Quiz doesn't exist"}, status=status.HTTP_403_FORBIDDEN)
            quizId = curriculumDetails.quizId
            questionString = json.dumps(questionJson)
            questionDetails = QuizQuestions.objects.create(question=questionString,
                                                           quiz_id=quizId,
                                                           correctAnswer=correctAnswer)
            questionDetails.save()
            return Response({Constants.JSON_MESSAGE: Constants.SUCCESS_MESSAGE}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetAllBatches(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(requestUserToken)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            user = UserDetails.objects.filter(userId=userId).first()
            batchIdDetails = Batch.objects.filter(tag_id=user.tag_id).values()
            batchIds = []
            for batchId in batchIdDetails:
                batchIds.append(
                    {Constants.BATCH_ID: batchId[Constants.BATCH_ID], Constants.BATCH_NAME: batchId[Constants.BATCH_NAME],
                     "timeDay": batchId['timeDay'],
                     "timeSchedule": batchId['timeSchedule'], "numberOfStudents": batchId['numberOfStudents'],
                     "active": batchId['active'], Constants.LATEST_LEVEL_ID: batchId[Constants.LATEST_LEVEL_ID],
                     Constants.LATEST_CLASS_ID: batchId[Constants.LATEST_CLASS_ID],
                     Constants.LATEST_LINK: batchId[Constants.LATEST_LINK]})
            return Response({"batches": batchIds})
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddBatch(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            timeDay = data['timeDay']
            timeSchedule = data['timeSchedule']
            batchName = data[Constants.BATCH_NAME]
            teacherUserId = data[Constants.USER_ID]
            user = UserDetails.objects.filter(userId=teacherUserId).first()
            if user.role != Constants.TEACHER:
                return Response({Constants.JSON_MESSAGE: "Given User is not a Teacher"}, status=status.HTTP_403_FORBIDDEN)
            else:
                newBatch = Batch.objects.create(
                    timeDay=timeDay,
                    timeSchedule=timeSchedule,
                    numberOfStudents=0,
                    active=True,
                    batchName=batchName,
                    latestLevelId=1,
                    latestClassId=1,
                    tag_id=user.tag_id
                )

                teacher = Teacher.objects.create(
                    user_id=teacherUserId,
                    batchId=newBatch.batchId
                )
                teacher.save()
                newBatch.save()
                return Response({Constants.JSON_MESSAGE: Constants.SUCCESS_MESSAGE}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetBatch(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            batchId = data[Constants.BATCH_ID]
            batchDetails = Batch.objects.filter(batchId=batchId).first()
            return Response({
                Constants.BATCH_ID: batchDetails.batchId,
                "timeDay": batchDetails.timeDay,
                "timeSchedule": batchDetails.timeSchedule,
                "numberOfStudents": batchDetails.numberOfStudents,
                "active": batchDetails.active,
                Constants.BATCH_NAME: batchDetails.batchName,
                Constants.LATEST_LEVEL_ID: batchDetails.latestLevelId,
                Constants.LATEST_CLASS_ID: batchDetails.latestClassId
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EditBatchDetails(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            batchId = data[Constants.BATCH_ID]
            timeDay = data['timeDay']
            timeSchedule = data['timeSchedule']
            batchName = data[Constants.BATCH_NAME]
            numberOfStudents = data['numberOfStudents']
            active = data['active']
            latestLevelId = data[Constants.LATEST_LEVEL_ID]
            latestClassId = data[Constants.LATEST_CLASS_ID]
            batchDetails = Batch.objects.filter(batchId=batchId).first()
            batchDetails.timeDay = timeDay
            batchDetails.timeSchedule = timeSchedule
            batchDetails.batchName = batchName
            batchDetails.numberOfStudents = numberOfStudents
            batchDetails.active = active
            batchDetails.latestLevelId = latestLevelId
            batchDetails.latestClassId = latestClassId
            batchDetails.save()
            return Response({Constants.JSON_MESSAGE: Constants.SUCCESS_MESSAGE}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteBatch(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            batchId = data[Constants.BATCH_ID]
            batchStudents = Student.objects.filter(batch_id=batchId).first()
            if batchStudents:
                return Response({Constants.JSON_MESSAGE: "Cannot Delete the batch as it has students in it"},
                                status=status.HTTP_403_FORBIDDEN)
            batchDetails = Batch.objects.filter(batchId=batchId).first()
            batchDetails.delete()
            return Response({Constants.JSON_MESSAGE: Constants.SUCCESS_MESSAGE}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddTeacher(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(requestUserToken)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            user = UserDetails.objects.filter(userId=userId).first()
            if user.role == Constants.SUB_ADMIN:
                data = request.data
                password = generatePassword()
                firstName = data[Constants.FIRST_NAME]
                lastName = data[Constants.LAST_NAME]
                phoneNumber = data[Constants.PHONE_NUMBER]
                email = data[Constants.EMAIL]
                email = email.lower()
                tag = user.tag_id
                if UserDetails.objects.filter(email=email).first() is not None:
                    return Response({Constants.JSON_MESSAGE: "User with this email already Exists"},
                                    status=status.HTTP_400_BAD_REQUEST)
                user = UserDetails.objects.create(
                    firstName=firstName,
                    lastName=lastName,
                    phoneNumber=phoneNumber,
                    email=email,
                    role=Constants.TEACHER,
                    encryptedPassword=encryptPassword(password),
                    created_date=datetime.datetime.now(),
                    blocked=False,
                    tag_id=tag
                )
                user.save()

                organizationDetails = OrganizationTag.objects.filter(tagId=user.tag_id).first()
                organizationDetails.numberOfTeachers += 1
                organizationDetails.save()
                email = EmailMessage(
                    'Account has been Created',
                    "An account has been created for this email id for the teacher role. The password is " + password + ". Please login and change your password",
                    'boltabacus.dev@gmail.com',
                    [email, 'boltabacus.dev@gmail.com']
                )
                email.send()

                return Response({Constants.JSON_MESSAGE: Constants.SUCCESS_MESSAGE},
                                status=status.HTTP_200_OK)
            else:
                return Response({Constants.JSON_MESSAGE: "User is not an admin"}, status=status.HTTP_401_UNAUTHORIZED)

        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetTeachers(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(requestUserToken)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            user = UserDetails.objects.filter(userId=userId).first()
            teacherDetails = UserDetails.objects.filter(role=Constants.TEACHER, tag_id=user.tag_id)
            teachers = []
            for teacher in teacherDetails:
                teachers.append({Constants.USER_ID: teacher.userId,
                                 Constants.FIRST_NAME: teacher.firstName,
                                 Constants.LAST_NAME: teacher.lastName})
            return Response({"teachers": teachers}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# class AssignBatch(APIView):
#     permission_classes = [AllowAny]
#
#     def post(self, request):
#         try:
#             data = request.data
#             teacherId = data[Constants.USER_ID]
#             teacher = UserDetails.objects.filter(userId=teacherId).first()
#             if teacher:
#                 if teacher.role == Constants.TEACHER:
#                     batchId = data[Constants.BATCH_ID]
#                     return assignUserToBatch(Teacher, batchId, teacherId, Constants.TEACHER)
#                 else:
#                     return Response({Constants.JSON_MESSAGE: "Given user is not a teacher"},
#                                     status=status.HTTP_403_FORBIDDEN)
#             else:
#                 return Response({Constants.JSON_MESSAGE: "Given user doesn't exist"},
#                                 status=status.HTTP_403_FORBIDDEN)
#         except Exception as e:
#             return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# class AssignStudentToBatch(APIView):
#     permission_classes = [AllowAny]
#
#     def post(self, request):
#         try:
#             data = request.data
#             studentId = data[Constants.USER_ID]
#             student = UserDetails.objects.filter(userId=studentId).first()
#             if student:
#                 if student.role == Constants.STUDENT:
#                     batchId = data[Constants.BATCH_ID]
#                     return assignUserToBatch(Student, batchId, studentId, Constants.STUDENT)
#                 else:
#                     return Response({Constants.JSON_MESSAGE: "Given user is not a Student"},
#                                     status=status.HTTP_403_FORBIDDEN)
#
#             else:
#                 return Response({Constants.JSON_MESSAGE: "Given user doesn't exist"},
#                                 status=status.HTTP_403_FORBIDDEN)
#
#             pass
#         except Exception as e:
#             return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddStudent(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        requestUserToken = request.headers[Constants.TOKEN_HEADER]
        try:
            userId = IdExtraction(requestUserToken)
            if isinstance(userId, Exception):
                raise Exception(requestUserToken)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
        user = UserDetails.objects.filter(userId=userId).first()
        if user.role == Constants.SUB_ADMIN:
            organizationDetails = OrganizationTag.objects.filter(tagId=user.tag_id).first()
            if (organizationDetails.totalNumberOfStudents - organizationDetails.numberOfStudents) <= 0:
                return Response({Constants.JSON_MESSAGE: "The account has reached maximum student it can add. Please "
                                                         "contact the administration to increase the limit."},
                                status=status.HTTP_403_FORBIDDEN)
            return createUser(request.data, Student, Constants.STUDENT, organizationDetails)
        else:
            return Response({Constants.JSON_MESSAGE: "User is not an admin"}, status=status.HTTP_401_UNAUTHORIZED)


class GetStudents(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            batchId = request.data[Constants.BATCH_ID]
            StudentList = getStudentIds(batchId)
            students = []

            for i in StudentList:
                student = UserDetails.objects.filter(userId=i).first()
                students.append({Constants.USER_ID: student.userId,
                                 Constants.FIRST_NAME: student.firstName,
                                 Constants.LAST_NAME: student.lastName})
            return Response({"students": students}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetTopicsData(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            requestLevelId = data[Constants.LEVEL_ID]
            topicDetails = TopicDetails.objects.filter(levelId=requestLevelId)
            topicDetailsDictionary = {}
            for topic in topicDetails:
                try:
                    topicDetailsDictionary[topic.classId].append(topic.topicId)
                except:
                    topicDetailsDictionary[topic.classId] = [topic.topicId]
            classData = []
            for i in topicDetailsDictionary:
                classData.append({Constants.CLASS_ID: i, 'topicIds': topicDetailsDictionary[i]})
            classData = (sorted(classData, key=lambda x: x[Constants.CLASS_ID]))
            return Response({"schema": classData}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def getStudentIds(batchId):
    studentIdDetails = Student.objects.filter(batch_id=batchId).values("user_id")
    studentIds = []
    for studentId in studentIdDetails:
        studentIds.append(studentId['user_id'])
    return studentIds


def getBatchList():
    batchIdDetails = Batch.objects.all().values(Constants.BATCH_ID)
    batchIds = []
    for batchId in batchIdDetails:
        batchIds.append(batchId[Constants.BATCH_ID])
    return batchIds


def createUser(data, dbObject, role, organizationTag):
    try:

        firstName = data[Constants.FIRST_NAME]
        lastName = data[Constants.LAST_NAME]
        phoneNumber = data[Constants.PHONE_NUMBER]
        emailId = data[Constants.EMAIL]
        emailId = emailId.lower()
        if UserDetails.objects.filter(email=emailId).first() is not None:
            return Response({Constants.JSON_MESSAGE: "User with this emailId already Exists"},
                            status=status.HTTP_400_BAD_REQUEST)

        password = generatePassword()

        batchId = data[Constants.BATCH_ID]
        batchList = getBatchList()
        if batchId in batchList:
            user = UserDetails.objects.create(
                firstName=firstName,
                lastName=lastName,
                phoneNumber=phoneNumber,
                email=emailId,
                role=role,
                encryptedPassword=encryptPassword(password),
                created_date=datetime.datetime.now(),
                blocked=False,
                tag_id=organizationTag.tagId
            )
            user.save()

            roleRelatedObject = dbObject.objects.create(
                user=user,
                batch_id=batchId
            )
            roleRelatedObject.save()
            organizationTag.numberOfStudents += 1
            organizationTag.save()
            if role == Constants.STUDENT:
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
                "An account has been created for this emailId id for the student role. The password is " + password + ". Please login and change your password",
                'boltabacus.dev@gmail.com',
                [emailId, 'boltabacus.dev@gmail.com']
            )
            email.send()
            return Response({Constants.JSON_MESSAGE: Constants.SUCCESS_MESSAGE},
                            status=status.HTTP_200_OK)
        else:
            return Response({Constants.JSON_MESSAGE: "Given batch Id is invalid"},
                            status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        return Response({Constants.JSON_MESSAGE: repr(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# def assignUserToBatch(dbObject, batchId, userId, role):
#     batchList = getBatchList()
#     if batchId in batchList:
#         try:
#             dbObjectInstance = dbObject.objects.filter(
#                 user_id=userId
#             ).first()
#             if role == Constants.TEACHER:
#                 previousBatchId = dbObjectInstance.batchId
#                 dbObjectInstance.batchId = batchId
#             else:
#                 previousBatchId = dbObjectInstance.batch_id
#                 dbObjectInstance.batch_id = batchId
#             dbObjectInstance.save()
#             if role == Constants.STUDENT:
#                 addProgressIfNeeded(previousBatchId, batchId, userId)
#             return Response({Constants.JSON_MESSAGE: Constants.SUCCESS_MESSAGE},
#                             status=status.HTTP_200_OK)
#         except Exception as e:
#             return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#     else:
#
#         return Response({Constants.JSON_MESSAGE: "Given batch Id is invalid"},
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
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(requestUserToken)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            batchId = data[Constants.BATCH_ID]
            link = data["link"]
            batch = Batch.objects.filter(batchId=batchId).first()
            if batch is None:
                return Response({Constants.JSON_MESSAGE: "Batch doesn't exist."}, status=status.HTTP_403_FORBIDDEN)
            teacher = Teacher.objects.filter(user_id=userId, batchId=batchId).first()
            if teacher is None:
                return Response({Constants.JSON_MESSAGE: "This User is not the Teacher for this batch."},
                                status=status.HTTP_403_FORBIDDEN)
            batch.latestLink = link
            batch.save()
            return Response({Constants.JSON_MESSAGE: Constants.SUCCESS_MESSAGE}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetTeacherBatches(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(requestUserToken)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            user = UserDetails.objects.filter(userId=userId).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User doesn't exist."}, status=status.HTTP_403_FORBIDDEN)
            else:
                if user.role != Constants.TEACHER:
                    return Response({Constants.JSON_MESSAGE: "User is not a Teacher"}, status=status.HTTP_403_FORBIDDEN)

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
                    {Constants.BATCH_ID: batch.batchId, Constants.BATCH_NAME: batch.batchName,
                     "timings": batch.timeSchedule})
            return Response({"batches": batches})
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateClass(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(requestUserToken)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            batchId = data[Constants.BATCH_ID]
            batch = Batch.objects.filter(batchId=batchId).first()
            if batch is None:
                return Response({Constants.JSON_MESSAGE: "Batch Doesn't exist."}, status=status.HTTP_403_FORBIDDEN)
            latestLevel = batch.latestLevelId
            latestClass = batch.latestClassId
            teacher = Teacher.objects.filter(user_id=userId, batchId=batchId).first()
            user = UserDetails.objects.filter(userId=userId).first()
            if teacher is None:
                return Response({Constants.JSON_MESSAGE: "This User is not the Teacher for this batch."},
                                status=status.HTTP_403_FORBIDDEN)
            nextLevel, nextClass = getNextClass(latestLevel, latestClass, user.tag_id)
            if nextClass == -1 or nextLevel == -1:
                return Response({Constants.JSON_MESSAGE: "Max Level and Class"}, status=status.HTTP_403_FORBIDDEN)
            if nextClass == -2 or nextLevel == -2:
                return Response({Constants.JSON_MESSAGE: "Class is out of Range"}, status=status.HTTP_403_FORBIDDEN)
            if nextClass == -3 or nextLevel == -3:
                return Response({Constants.JSON_MESSAGE: "Level is out of Range"}, status=status.HTTP_403_FORBIDDEN)
            if nextLevel == -4 or nextClass == -4:
                return Response({Constants.JSON_MESSAGE: "This is the max level and class allowed. Please contact "
                                                         "the Administrator for further Details."},
                                status=status.HTTP_403_FORBIDDEN)

            students = Student.objects.filter(batch_id=batchId)
            curriculum = Curriculum.objects.filter(levelId=nextLevel, classId=nextClass)
            for student in students:
                for quiz in curriculum:
                    if (quiz.levelId < nextLevel) or (quiz.classId <= nextClass and
                                                      quiz.levelId == nextLevel):
                        if not progressPresent(quiz.quizId, student.user_id):
                            progress = Progress.objects.create(
                                quiz_id=quiz.quizId,
                                user_id=student.user_id
                            )
                            progress.save()

                    else:
                        break
            batch.latestClassId = nextClass
            batch.latestLevelId = nextLevel
            batch.save()
            return Response({Constants.JSON_MESSAGE: Constants.SUCCESS_MESSAGE, "level": nextLevel, "class": nextClass},
                            status=status.HTTP_200_OK)

        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetClassReport(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            batchId = data[Constants.BATCH_ID]
            levelId = data[Constants.LEVEL_ID]
            classId = data[Constants.CLASS_ID]
            topicId = data[Constants.TOPIC_ID]
            if levelId == 1 and classId == 1:
                return Response({Constants.JSON_MESSAGE: "This class doesn't have a quiz"},
                                status=status.HTTP_404_NOT_FOUND)
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                requestUserId = IdExtraction(requestUserToken)
                if isinstance(requestUserId, Exception):
                    raise Exception(requestUserToken)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            teacher = UserDetails.objects.filter(userId=requestUserId).first()
            if teacher is None:
                return Response({Constants.JSON_MESSAGE: "User doesn't exist."}, status=status.HTTP_403_FORBIDDEN)
            if teacher.role != Constants.TEACHER:
                return Response({Constants.JSON_MESSAGE: "User is not a teacher."}, status=status.HTTP_403_FORBIDDEN)
            batchTeacher = Teacher.objects.filter(user_id=requestUserId, batchId=batchId).first()
            if batchTeacher is None:
                return Response({Constants.JSON_MESSAGE: "Teacher is not assigned to the batch."},
                                status=status.HTTP_403_FORBIDDEN)
            classwork = Curriculum.objects.filter(levelId=levelId,
                                                  classId=classId,
                                                  topicId=topicId,
                                                  quizType=Constants.CLASSWORK).first()

            homework = Curriculum.objects.filter(levelId=levelId,
                                                 classId=classId,
                                                 topicId=topicId,
                                                 quizType=Constants.HOMEWORK).first()

            test = Curriculum.objects.filter(levelId=levelId,
                                             classId=classId,
                                             topicId=0,
                                             quizType=Constants.TEST).first()
            classworkQuizId = classwork.quizId
            homeworkQuizId = homework.quizId
            testId = test.quizId
            students = Student.objects.filter(batch_id=batchId)
            studentReports = []
            for student in students:
                userId = student.user_id
                user = UserDetails.objects.filter(userId=userId).first()
                classworkProgress = Progress.objects.filter(quiz_id=classworkQuizId,
                                                            user_id=userId).first()
                homeworkProgress = Progress.objects.filter(quiz_id=homeworkQuizId,
                                                           user_id=userId).first()
                testProgress = Progress.objects.filter(quiz_id=testId,
                                                       user_id=userId).first()
                if classworkProgress is None or homeworkProgress is None or testProgress is None:
                    return Response(
                        {Constants.JSON_MESSAGE: "Report not found for student " + user.firstName + user.lastName},
                        status=status.HTTP_404_NOT_FOUND)
                studentReports.append({Constants.USER_ID: user.userId,
                                       Constants.FIRST_NAME: user.firstName,
                                       Constants.LAST_NAME: user.lastName,
                                       "classwork": classworkProgress.percentage,
                                       "homework": homeworkProgress.percentage,
                                       "test": testProgress.percentage})
            return Response({"reports": studentReports}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetStudentProgress(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            userId = data[Constants.USER_ID]
            return getStudentProgress(userId)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetStudentProgressFromStudent(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(userId)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            return getStudentProgress(userId)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def getStudentProgress(userId):
    try:
        user = UserDetails.objects.filter(userId=userId).first()
        if user is None:
            return Response({Constants.JSON_MESSAGE: "User doesn't exist."}, status=status.HTTP_404_NOT_FOUND)
        if user.role != Constants.STUDENT:
            return Response({Constants.JSON_MESSAGE: "User is not a Student"}, status=status.HTTP_403_FORBIDDEN)
        student = Student.objects.filter(user_id=userId).first()
        batchId = student.batch_id
        batch = Batch.objects.filter(batchId=batchId).first()
        studentProgress = Progress.objects.filter(user_id=userId)
        levelsProgress = {}
        for progress in studentProgress:
            curriculum = Curriculum.objects.filter(quizId=progress.quiz_id).first()
            levelId = curriculum.levelId
            classId = curriculum.classId
            topicId = curriculum.topicId
            counter = True
            if classId == 1 and levelId == 1:
                counter = False
            if counter:
                try:
                    classProgress = levelsProgress[levelId]
                except:
                    levelsProgress[levelId] = {}
                    classProgress = levelsProgress[levelId]
                try:
                    topicProgress = classProgress[classId]
                except:
                    classProgress[classId] = {}
                    topicProgress = classProgress[classId]
                try:
                    topicProgress[topicId].update(
                        {curriculum.quizType: progress.percentage, curriculum.quizType + "Time": progress.time})
                except:
                    topicProgress[topicId] = {curriculum.quizType: progress.percentage,
                                              curriculum.quizType + "Time": progress.time}
        levelsProgressData = []
        for levelId in levelsProgress:
            levelsProgressJson = {Constants.LEVEL_ID: levelId}
            classProgressData = []
            classProgress = levelsProgress[levelId]
            for classId in classProgress:
                classProgressJson = {Constants.CLASS_ID: classId}
                topicProgress = classProgress[classId]
                topicProgressData = []
                for topicId in topicProgress:
                    if topicId != 0:
                        result = topicProgress[topicId]
                        topicProgressData.append({Constants.TOPIC_ID: topicId,
                                                  Constants.CLASSWORK: result[Constants.CLASSWORK],
                                                  Constants.CLASSWORK_TIME: result[Constants.CLASSWORK_TIME],
                                                  Constants.HOMEWORK: result[Constants.HOMEWORK],
                                                  Constants.HOMEWORK_TIME: result[Constants.HOMEWORK_TIME]})
                classProgressJson.update(
                    {Constants.TEST: topicProgress[0][Constants.TEST], "Time": topicProgress[0][Constants.TEST_TIME]})
                classProgressJson.update({"topics": topicProgressData})
                classProgressData.append(classProgressJson)
            levelsProgressJson.update({"classes": classProgressData})
            levelsProgressData.append(levelsProgressJson)
        for classes in levelsProgressData:
            classes['classes'] = sorted(classes['classes'], key=lambda x: x[Constants.CLASS_ID])
            for topics in classes['classes']:
                topics['topics'] = sorted(topics['topics'], key=lambda x: x[Constants.TOPIC_ID])

        return Response({Constants.FIRST_NAME: user.firstName,
                         Constants.LAST_NAME: user.lastName,
                         Constants.BATCH_NAME: batch.batchName,
                         "levels": levelsProgressData}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def getClassIds(levelId):
    classIds = set()
    classes = TopicDetails.objects.filter(levelId=levelId)
    for eachClass in classes:
        classIds.add(eachClass.classId)
    return classIds


def getNextClass(levelId, classId, tag_id):
    organizationsDetails = OrganizationTag.objects.filter(tagId=tag_id)
    maxLevelAllowed = organizationsDetails.maxLevel
    maxClassAllowed = organizationsDetails.maxClass
    if classId > 12 or classId < 0:
        return -2, -2
    if levelId > 10 or levelId < 0:
        return -3, -3
    if levelId > maxLevelAllowed or (levelId == maxLevelAllowed and classId > maxClassAllowed):
        return -4, -4
    if classId == 12:
        if levelId != 10:
            return levelId + 1, 1
        else:
            return -1, -1
    else:
        return levelId, classId + 1


def progressPresent(quizId, userId):
    progress = Progress.objects.filter(quiz_id=quizId, user_id=userId).first()
    if progress is None:
        return False
    else:
        return True


class BulkAddQuestions(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            requestLevelId = data[Constants.LEVEL_ID]
            requestClassId = data[Constants.CLASS_ID]
            requestQuizType = data[Constants.QUIZ_TYPE]
            requestTopicId = data[Constants.TOPIC_ID]
            questions = data[Constants.QUESTIONS]
            if requestQuizType == Constants.TEST:
                curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
                                                              classId=requestClassId,
                                                              quizType=requestQuizType).first()
            else:
                curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
                                                              classId=requestClassId,
                                                              topicId=requestTopicId,
                                                              quizType=requestQuizType).first()
            if curriculumDetails is None:
                return Response({Constants.JSON_MESSAGE: "Quiz doesn't exist"}, status=status.HTTP_404_NOT_FOUND)
            quizId = curriculumDetails.quizId
            QuizQuestions.objects.filter(quiz_id=quizId).delete()
            for questionIndex in questions:

                questionJson = questionIndex[Constants.QUESTION]
                correctAnswer = questionIndex[Constants.CORRECT_ANSWER]
                questionString = json.dumps(questionJson)
                questionObject = QuizQuestions.objects.create(question=questionString,
                                                              quiz_id=quizId,
                                                              correctAnswer=correctAnswer)
                questionObject.save()
            return Response({Constants.JSON_MESSAGE: Constants.SUCCESS_MESSAGE}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ForgotPassword(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        email = data[Constants.EMAIL].lower()
        user = UserDetails.objects.filter(email=email).first()
        if user is not None:

            organization = OrganizationTag.objects.filter(tagId=user["tag_id"]).first()
            organizationExpirationDate = organization.expirationDate
            payload = {
                Constants.USER_ID: user.userId,
                Constants.ROLE: user.role,
                Constants.EXPIRY_TIME: str(datetime.datetime.utcnow() + datetime.timedelta(minutes=60)),
                "creationTime": str(datetime.datetime.utcnow()),
                Constants.ORGANIZATION_EXPIRATION_DATE: str(organizationExpirationDate)

            }
            secretKey = Constants.SECRET_KEY
            loginToken = jwt.encode(payload, secretKey, algorithm='HS256')
            userName = user.firstName + " " + user.lastName
            sendLinkEmail(loginToken, userName, email)
            return Response({Constants.JSON_MESSAGE: Constants.SUCCESS_MESSAGE}, status=status.HTTP_200_OK)
        else:
            return Response({Constants.JSON_MESSAGE: "The user doesn't exist"}, status=status.HTTP_404_NOT_FOUND)


class ResetPasswordV2(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            requestUserToken = data['token']
            if not checkExpiry(requestUserToken):
                return Response({Constants.JSON_MESSAGE: "Token has Expired."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                requestUserId = IdExtraction(requestUserToken)
                if isinstance(requestUserId, Exception):
                    raise Exception(requestUserToken)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            password = data[Constants.PASSWORD]
            user = UserDetails.objects.filter(userId=requestUserId).first()
            user.encryptedPassword = password
            user.save()
            return Response({Constants.JSON_MESSAGE: Constants.SUCCESS_MESSAGE}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def checkExpiry(token):
    try:
        secretKey = Constants.SECRET_KEY
        payload = jwt.decode(token, secretKey, algorithms=['HS256'])
        expiryTime = payload[Constants.EXPIRY_TIME].split(".")[0]
        convertedExpiryTime = datetime.datetime.strptime(expiryTime, "%Y-%m-%d %H:%M:%S")
        if convertedExpiryTime < datetime.datetime.utcnow():
            return False
        return True
    except Exception as e:
        return e


def sendLinkEmail(token, userName, emailId):
    url = "boltabacus.com/resetPassword/v2/" + token
    content = {
        'url': url,
        "name": userName
    }
    template = loader.get_template('ForgotPasswordTemplate.html').render(content)
    email = EmailMessage(
        "Link To change your Password",
        template,
        'boltabacus.dev@gmail.com',
        [emailId]
    )
    email.content_subtype = 'html'
    result = email.send()
    return result


# -------------------- Sub-Admin Related APIs ----------------------

class AddSubAdmin(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            password = generatePassword()
            firstName = data[Constants.FIRST_NAME]
            lastName = data[Constants.LAST_NAME]
            phoneNumber = data[Constants.PHONE_NUMBER]
            email = data[Constants.EMAIL].lower()
            tagName = data[Constants.TAG_NAME]
            orgTag = OrganizationTag.objects.filter(tagName=tagName).first()
            if UserDetails.objects.filter(email=email).first() is not None:
                return Response({Constants.JSON_MESSAGE: "User with this email already Exists"},
                                status=status.HTTP_400_BAD_REQUEST)
            user = UserDetails.objects.create(
                firstName=firstName,
                lastName=lastName,
                phoneNumber=phoneNumber,
                email=email,
                role=Constants.SUB_ADMIN,
                encryptedPassword=encryptPassword(password),
                created_date=datetime.datetime.now(),
                blocked=False,
                tag_id=orgTag.tagId
            )
            user.save()
            email = EmailMessage(
                'Account has been Created',
                "An account has been created for this email id for the sub-Admin role. The password is " + password + ". Please login and change your password",
                'boltabacus.dev@gmail.com',
                [email, 'boltabacus.dev@gmail.com']
            )
            email.send()

            return Response({Constants.JSON_MESSAGE: Constants.SUCCESS_MESSAGE},
                            status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetAllOrganizationTagNames(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            organizations = OrganizationTag.objects.all()
            tagNames = []
            for organization in organizations:
                tagNames.append(organization.tagName)
            return Response({"tagNames": tagNames}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddOrganizationTagDetails(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(userId)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            requestData = request.data
            date = requestData[Constants.EXPIRATION_DATE].split("-")
            dateAccToDB = datetime.date(int(date[0]), int(date[1]), int(date[2]))
            OrganizationTag.objects.create(
                organizationName=requestData[Constants.ORGANIZATION_NAME],
                tagName=requestData[Constants.TAG_NAME],
                isIndividualTeacher=requestData[Constants.IS_INDIVIDUAL_TEACHER],
                numberOfTeachers=requestData[Constants.NUMBER_OF_TEACHERS],
                numberOfStudents=requestData[Constants.NUMBER_OF_STUDENTS],
                expirationDate=dateAccToDB,
                totalNumberOfStudents=requestData[Constants.TOTAL_NUMBER_OF_STUDENTS],
                maxLevel=requestData[Constants.MAX_LEVEL],
                maxClass=requestData[Constants.MAX_CLASS]
            )
            return Response({Constants.JSON_MESSAGE: Constants.SUCCESS_MESSAGE}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetOrganizationTagDetails(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(userId)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            requestData = request.data
            tagName = requestData[Constants.TAG_NAME]
            organization = OrganizationTag.objects.filter(tagName=tagName).first()
            if organization is None:
                return Response({Constants.JSON_MESSAGE: "Tag Not Found."}, status=status.HTTP_404_NOT_FOUND)
            return Response({
                Constants.TAG_ID: organization.tagId,
                Constants.ORGANIZATION_NAME: organization.organizationName,
                Constants.TAG_NAME: organization.tagName,
                Constants.IS_INDIVIDUAL_TEACHER: organization.isIndividualTeacher,
                Constants.NUMBER_OF_TEACHERS: organization.numberOfTeachers,
                Constants.NUMBER_OF_STUDENTS: organization.numberOfStudents,
                Constants.EXPIRATION_DATE: organization.expirationDate,
                Constants.TOTAL_NUMBER_OF_STUDENTS: organization.totalNumberOfStudents,
                Constants.MAX_LEVEL: organization.maxLevel,
                Constants.MAX_CLASS: organization.maxClass
            })

        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateOrganizationDetails(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(userId)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            requestData = request.data
            date = requestData[Constants.EXPIRATION_DATE].split("-")
            dateAccToDB = datetime.date(int(date[0]), int(date[1]), int(date[2]))
            organization = OrganizationTag.objects.filter(tagName=requestData[Constants.TAG_NAME]).first()
            organization.organizationName = requestData[Constants.ORGANIZATION_NAME]
            organization.isIndividualTeacher = bool(requestData[Constants.IS_INDIVIDUAL_TEACHER])
            organization.numberOfTeachers = int(requestData[Constants.NUMBER_OF_TEACHERS])
            organization.numberOfStudents = int(requestData[Constants.NUMBER_OF_STUDENTS])
            organization.expirationDate = dateAccToDB
            organization.totalNumberOfStudents = int(requestData[Constants.TOTAL_NUMBER_OF_STUDENTS])
            organization.maxLevel = int(requestData[Constants.MAX_LEVEL])
            organization.maxClass = int(requestData[Constants.MAX_CLASS])
            organization.save()

            return Response({Constants.JSON_MESSAGE: Constants.SUCCESS_MESSAGE}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BulkAddStudents(APIView):

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(userId)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            user = UserDetails.objects.filter(userId=userId).first()
            role = user.role
            if role == Constants.SUB_ADMIN:
                data = request.data
                students = data['students']
                batchId = data[Constants.BATCH_ID]
                requestedNumberOfStudents = len(students)
                organizationDetails = OrganizationTag.objects.filter(tagId=user.tag_id).first()
                if (
                        organizationDetails.totalNumberOfStudents - organizationDetails.numberOfStudents) < requestedNumberOfStudents:
                    return Response(
                        {Constants.JSON_MESSAGE: "The account is trying to add more students than the maximum number "
                                                 "of students it can add. Please contact the administration to "
                                                 "increase the limit."},
                        status=status.HTTP_403_FORBIDDEN)
                existingStudents = []
                nonExistingStudents = []
                studentsNotAdded = []
                errorMessage = ""
                for i in range(len(students)):
                    tempUserObject = UserDetails.objects.filter(email=students[i].email)
                    if tempUserObject is not None:
                        existingStudents.append(i)
                        errorMessage += ("The addition of the student with the email ID "
                                         + str(students[i][Constants.EMAIL])
                                         + "has not been completed due to an existing account associated with the "
                                           "same email address. \n")
                    else:
                        nonExistingStudents.append(i)
                for i in nonExistingStudents:
                    try:
                        studentData = {
                            "firstName": students[i][Constants.FIRST_NAME],
                            "lastName": students[i][Constants.LAST_NAME],
                            "phoneNumber": students[i][Constants.PHONE_NUMBER],
                            "emailId": students[i][Constants.EMAIL],
                            "batchId": batchId
                        }
                        createUser(studentData, Student, Constants.STUDENT, organizationDetails)
                    except Exception as e:
                        studentsNotAdded.append(i)
                if len(studentsNotAdded) != 0:
                    for i in studentsNotAdded:
                        errorMessage += ("The addition of the student with the email ID "
                                         + str(students[i][Constants.EMAIL])
                                         + "Because their might be error with the details provided or else please "
                                           "contact the administrator")

            else:
                return Response({Constants.JSON_MESSAGE: "User is not an admin"}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def temp():
    print(TopicDetails.objects.filter(levelId=3).values())
    print(OrganizationTag.objects.all().values())
    # user = UserDetails.objects.filter(userId=120).first()
    # print(user.tag_id)
    print(Batch.objects.all().values())
    # print(Curriculum.objects.filter(levelId=1, classId=4).values(), "\n")
    # print(Progress.objects.filter(user_id=2).values())

# Create your views here.
