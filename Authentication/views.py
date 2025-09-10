import datetime
from django.utils import timezone
import random
import time
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
                                   Progress, Teacher, OrganizationTag,
                                   PracticeQuestions, UserExperience, PVPRoom, 
                                   PVPRoomPlayer, PVPGameSession, PVPPlayerAnswer, 
                                   PVPGameResult, UserStreak, UserCoins, UserAchievement)
from rest_framework.decorators import api_view


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
            if user[Constants.BLOCKED] == True:
                return Response({Constants.JSON_MESSAGE: "The user has been deactivated, Please contact the administrator"}, status=status.HTTP_403_FORBIDDEN)
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
                    "userId": user[Constants.USER_ID],
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



class CurrentLevelsV2(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            auth_token = request.headers.get(Constants.TOKEN_HEADER)
            if not auth_token:
                return Response({Constants.JSON_MESSAGE: "Authentication token required"}, status=status.HTTP_401_UNAUTHORIZED)
            
            try:
                payload = jwt.decode(auth_token, Constants.SECRET_KEY, algorithms=['HS256'])
                user_id = payload.get(Constants.USER_ID)
                if not user_id:
                    return Response({Constants.JSON_MESSAGE: "Invalid token payload"}, status=status.HTTP_401_UNAUTHORIZED)
                
                user_details = UserDetails.objects.filter(userId=user_id).first()
                if not user_details:
                    return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
                
                requestUserId = user_details
            except jwt.ExpiredSignatureError:
                return Response({Constants.JSON_MESSAGE: "Token has expired"}, status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({Constants.JSON_MESSAGE: "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            
            userBatchDetails = Student.objects.filter(user=requestUserId).first()
            if userBatchDetails is None:
                return Response({Constants.JSON_MESSAGE: "Given user is Invalid or not a Student."}, status=status.HTTP_400_BAD_REQUEST)
            userBatchId = userBatchDetails.batch_id
            userBatch = Batch.objects.filter(batchId=userBatchId).first()
            latestLevel = userBatchDetails.latestLevelId
            latestLink = userBatch.latestLink
            latestClass = userBatchDetails.latestClassId
            levelsPercentage = {}
            
            # Get all progress records for this user in one query
            user_progress = Progress.objects.filter(user_id=requestUserId.userId).values('quiz_id', 'quizPass')
            progress_dict = {p['quiz_id']: p['quizPass'] for p in user_progress}
            
            for level in range(1, latestLevel + 1):
                latestClassId = 12
                topicCount = 0
                numberOfTopicsPassed = 0
                
                # Get all curriculum for this level in one query
                curriculum_details = Curriculum.objects.filter(levelId=level)
                
                for curriculum in curriculum_details:
                    currentClassId = curriculum.classId
                    if latestLevel > level or (latestClass >= currentClassId and level == latestLevel):
                        topicCount += 1
                    quizId = curriculum.quizId
                    if quizId in progress_dict and progress_dict[quizId]:
                        numberOfTopicsPassed += 1
                    else:
                        topicCount += 1
                
                if topicCount > 0:
                    percentage = int((numberOfTopicsPassed / topicCount) * 100)
                else:
                    percentage = 0
                levelsPercentage[level] = percentage 
            return Response({"levelsPercentage": levelsPercentage,
                             Constants.LEVEL_ID: latestLevel, 
                             Constants.LATEST_CLASS: latestClass,
                             Constants.LATEST_LINK: latestLink}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    


class ClassProgress(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            data = request.data
            requestLevelId = data[Constants.LEVEL_ID]
            try:
                requestUserId = IdExtraction(requestUserToken)
                if isinstance(requestUserId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            userBatchDetails = Student.objects.filter(user=requestUserId).first()
            if userBatchDetails is None:
                return Response({Constants.JSON_MESSAGE: "Given user is Invalid or not a Student."}, status=status.HTTP_400_BAD_REQUEST)
            latestLevel = userBatchDetails.latestLevelId
            latestClass = userBatchDetails.latestClassId
            progressData = []
            if requestLevelId <= 0 or requestLevelId > 10 or latestLevel < requestLevelId:
                return Response({Constants.JSON_MESSAGE: "Level not accessible."}, status=status.HTTP_403_FORBIDDEN)
            elif latestLevel >= requestLevelId:
                if requestLevelId < latestLevel:
                    latestClass = 12
                finalTestPercentage = 0
                oralTestPercentage = 0
                finalTestTime = 0
                oralTestTime = 0
                for currentClassId in range(0, latestClass + 1):
                    curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId, classId=currentClassId)
                    classProgress = {}
                    for quiz in curriculumDetails:
                        quizId = quiz.quizId
                        progress = Progress.objects.filter(quiz_id=quizId, user_id=requestUserId).first()
                        try:
                            classProgress[quiz.topicId].update(
                                {quiz.quizType: {Constants.PERCENTAGE: progress.percentage,
                            Constants.TIME: progress.time}
                                })
                        except:
                            classProgress[quiz.topicId] = {
                                quiz.quizType: {Constants.PERCENTAGE: progress.percentage,
                                Constants.TIME: progress.time}
                                }
                    if currentClassId != 0:
                        progressData.append({Constants.CLASS_ID: currentClassId, "topics": classProgress})
                    else:
                        finalTestPercentage = classProgress[0][Constants.FINAL_TEST][Constants.PERCENTAGE]
                        oralTestPercentage = classProgress[0][Constants.ORAL_TEST][Constants.TIME]
                        finalTestTime = classProgress[0][Constants.FINAL_TEST][Constants.PERCENTAGE]
                        oralTestTime = classProgress[0][Constants.ORAL_TEST][Constants.TIME]
                return Response({Constants.PROGRESS: progressData,
                                "finalTest": {Constants.PERCENTAGE: finalTestPercentage, Constants.TIME: finalTestTime},
                                "oralTest": {Constants.PERCENTAGE: oralTestPercentage, Constants.TIME: oralTestTime}},
                                status=status.HTTP_200_OK)
            else:
                return Response({Constants.JSON_MESSAGE: "Level not accessible."}, status=status.HTTP_403_FORBIDDEN)
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
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
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
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            userBatchDetails = Student.objects.filter(user=requestUserId).first()
            latestLevel = userBatchDetails.latestLevelId
            latestClass = userBatchDetails.latestClassId

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
            elif requestQuizType == Constants.ORAL_TEST or requestQuizType == Constants.FINAL_TEST:
                curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
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
                try:
                    requestUserId = IdExtraction(idToken)
                    if isinstance(requestUserId, Exception):
                        raise Exception(Constants.INVALID_TOKEN_MESSAGE)
                except Exception as e:
                    return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
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
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            data = request.data
            requestLevelId = data[Constants.LEVEL_ID]
            requestClassId = data[Constants.CLASS_ID]
            userBatchDetails = Student.objects.filter(user=requestUserId).first()
            latestLevel = userBatchDetails.latestLevelId
            latestClass = userBatchDetails.latestClassId
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
            if requestClassId != 0:
                test = {Constants.TEST: topicProgress[0][Constants.TEST], "Time": topicProgress[0][Constants.TEST_TIME]}
                return Response({"quiz": progressOfTopics, "test": test})

            finalTest = {Constants.FINAL_TEST: topicProgress[0][Constants.FINAL_TEST], Constants.FINAL_TEST_TIME: topicProgress[0][Constants.FINAL_TEST_TIME]}
            oralTest = {Constants.ORAL_TEST: topicProgress[0][Constants.ORAL_TEST], Constants.ORAL_TEST_TIME: topicProgress[0][Constants.ORAL_TEST_TIME]}
            return Response({"quiz": progressOfTopics, "finalTest": finalTest, "oralTest": oralTest})
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
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
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
    
    # Handle single-number operations with descriptive text
    if operator == '√':
        return f"Square root of {numbers[0]}"
    elif operator == '∛':
        return f"Cube root of {numbers[0]}"
    elif operator == '²':
        return f"Square of {numbers[0]}"
    elif operator == '³':
        return f"Cube of {numbers[0]}"
    
    # Handle two-number operations
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

def calculateAbacusStyle(question_str):
    """
    Calculate abacus-style (left-to-right, no BODMAS) and avoid fractions
    Handles special operations like squares (²) and square roots (√)
    """
    import re
    
    try:
        # Remove the " = ?" part
        expression = question_str.replace(" = ?", "")
        
        # Replace × with * and ÷ with / for easier parsing
        expression = expression.replace(" × ", " * ").replace(" ÷ ", " / ")
        
        # Handle special operations first (squares and roots)
        # Process squares (²) - apply to the number before it
        while '²' in expression:
            # Find pattern: number²
            match = re.search(r'(\d+)²', expression)
            if match:
                num = int(match.group(1))
                squared = num ** 2
                expression = expression.replace(match.group(0), str(squared))
            else:
                break
        
        # Process square roots (√) - apply to the number before it
        while '√' in expression:
            # Find pattern: number√
            match = re.search(r'(\d+)√', expression)
            if match:
                num = int(match.group(1))
                # For abacus, use integer square root
                sqrt_val = int(num ** 0.5)
                expression = expression.replace(match.group(0), str(sqrt_val))
            else:
                break
        
        # Process cube roots (∛) - apply to the number before it
        while '∛' in expression:
            # Find pattern: number∛
            match = re.search(r'(\d+)∛', expression)
            if match:
                num = int(match.group(1))
                # For abacus, use integer cube root
                cbrt_val = int(num ** (1/3))
                expression = expression.replace(match.group(0), str(cbrt_val))
            else:
                break
        
        # Process cubes (³) - apply to the number before it
        while '³' in expression:
            # Find pattern: number³
            match = re.search(r'(\d+)³', expression)
            if match:
                num = int(match.group(1))
                cubed = num ** 3
                expression = expression.replace(match.group(0), str(cubed))
            else:
                break
        
        # Split by spaces to get numbers and operators
        tokens = expression.split()
        
        if len(tokens) < 3:
            return int(tokens[0]) if tokens else 0
        
        # Start with first number
        result = int(tokens[0])
        
        # Process left to right
        i = 1
        while i < len(tokens) - 1:
            operator = tokens[i]
            next_num = int(tokens[i + 1])
            
            if operator == '+':
                result += next_num
            elif operator == '-':
                result -= next_num
            elif operator == '*':
                result *= next_num
            elif operator == '/':
                # For division
                if next_num == 0:
                    next_num = 1  # no division by zero
                result = result // next_num
                if result == 0:
                    result = 1
            
            i += 2
        
        return result
    
    except Exception as e:
        print(f"Error in calculateAbacusStyle: {e}")
        print(f"Question string: {question_str}")
        # Return a simple fallback calculation
        try:
            # Simple fallback: just add all numbers
            numbers = re.findall(r'\d+', question_str)
            return sum(int(num) for num in numbers) if numbers else 1
        except:
            return 1

def generateOptions(correct_answer):
    """Generate 4 options with the correct answer and 3 wrong answers"""
    import random
    
    options = [correct_answer]
    
    # Generate 3 wrong options
    for _ in range(3):
        # Create wrong answers that are close to the correct answer
        if correct_answer > 10:
            wrong_answer = correct_answer + random.randint(-correct_answer//2, correct_answer//2)
        else:
            wrong_answer = correct_answer + random.randint(-5, 5)
        
        # Ensure wrong answer is positive and different from correct answer
        while wrong_answer <= 0 or wrong_answer in options:
            if correct_answer > 10:
                wrong_answer = correct_answer + random.randint(-correct_answer//2, correct_answer//2)
            else:
                wrong_answer = correct_answer + random.randint(-5, 5)
        
        options.append(wrong_answer)
    
    # Shuffle the options
    random.shuffle(options)
    return options

def generatePVPQuestion(difficulty_level='medium', number_of_digits=3):
    """
    Generate a math question based on difficulty level for PVP games.
    New format: Vertical operands with single operator
    
    Difficulty levels:
    - Easy: Addition & Subtraction only, operands 2-5 digits
    - Medium: Add, Sub, Multiply, operands 2-5 digits  
    - Hard: Add, Sub, Multiply, Divide, operands 5-10 digits
    - Expert: All + Square, Root, Cube, single operand for special operations
    """
    import random
    import math
    
    # Generate operands based on number_of_digits
    def generate_operand(digits):
        if digits == 1:
            return random.randint(1, 9)
        else:
            min_val = 10 ** (digits - 1)
            max_val = (10 ** digits) - 1
            return random.randint(min_val, max_val)
    
    if difficulty_level == 'easy':
        # Easy: Addition & Subtraction only, operands 2-5 digits
        operand_range = random.randint(2, 5)
        num_operands = random.randint(2, 4)
        operations = ['+', '-']
        
        operands = []
        for i in range(num_operands):
            operands.append(generate_operand(operand_range))
        
        operator = random.choice(operations)
        
        # Calculate answer
        if operator == '+':
            answer = sum(operands)
        else:  # subtraction
            # Ensure positive result
            answer = operands[0]
            for i in range(1, len(operands)):
                answer -= operands[i]
            if answer <= 0:
                # Regenerate to ensure positive result
                operands[0] = sum(operands[1:]) + random.randint(1, 100)
                answer = operands[0] - sum(operands[1:])
        
        return {
            'operands': operands,
            'operator': operator,
            'correct_answer': answer,
            'question_type': 'basic'
        }
    
    elif difficulty_level == 'medium':
        # Medium: Add, Sub, Multiply, operands 2-5 digits
        operand_range = random.randint(2, 5)
        num_operands = random.randint(2, 3)
        operations = ['+', '-', '*']
        
        operands = []
        for i in range(num_operands):
            operands.append(generate_operand(operand_range))
        
        operator = random.choice(operations)
        
        # Calculate answer
        if operator == '+':
            answer = sum(operands)
        elif operator == '-':
            answer = operands[0] - sum(operands[1:])
            if answer <= 0:
                operands[0] = sum(operands[1:]) + random.randint(1, 100)
                answer = operands[0] - sum(operands[1:])
        else:  # multiplication
            answer = 1
            for op in operands:
                answer *= op
        
        return {
            'operands': operands,
            'operator': operator,
            'correct_answer': answer,
            'question_type': 'basic'
        }
    
    elif difficulty_level == 'hard':
        # Hard: Add, Sub, Multiply, Divide, operands 5-10 digits
        operand_range = random.randint(5, 10)
        num_operands = random.randint(2, 3)
        operations = ['+', '-', '*', '/']
        
        operands = []
        for i in range(num_operands):
            operands.append(generate_operand(operand_range))
        
        operator = random.choice(operations)
        
        # Calculate answer
        if operator == '+':
            answer = sum(operands)
        elif operator == '-':
            answer = operands[0] - sum(operands[1:])
            if answer <= 0:
                operands[0] = sum(operands[1:]) + random.randint(1, 1000)
                answer = operands[0] - sum(operands[1:])
        elif operator == '*':
            answer = 1
            for op in operands:
                answer *= op
        else:  # division
            # Ensure clean division
            dividend = operands[0]
            divisor = operands[1]
            if dividend % divisor != 0:
                # Make it divisible
                dividend = divisor * random.randint(1, 100)
                operands[0] = dividend
            answer = dividend // divisor
        
        return {
            'operands': operands,
            'operator': operator,
            'correct_answer': answer,
            'question_type': 'basic'
        }
    
    else:  # expert
        # Expert: All + Square, Root, Cube, single operand for special operations
        question_types = ['basic', 'square', 'square_root', 'cube', 'cube_root']
        question_type = random.choice(question_types)
        
        if question_type == 'basic':
            # Basic operations with larger numbers
            operand_range = random.randint(3, 8)
            num_operands = random.randint(2, 3)
            operations = ['+', '-', '*', '/']
            
            operands = []
            for i in range(num_operands):
                operands.append(generate_operand(operand_range))
            
            operator = random.choice(operations)
            
            # Calculate answer
            if operator == '+':
                answer = sum(operands)
            elif operator == '-':
                answer = operands[0] - sum(operands[1:])
                if answer <= 0:
                    operands[0] = sum(operands[1:]) + random.randint(1, 1000)
                    answer = operands[0] - sum(operands[1:])
            elif operator == '*':
                answer = 1
                for op in operands:
                    answer *= op
            else:  # division
                dividend = operands[0]
                divisor = operands[1]
                if dividend % divisor != 0:
                    dividend = divisor * random.randint(1, 100)
                    operands[0] = dividend
                answer = dividend // divisor
            
            return {
                'operands': operands,
                'operator': operator,
                'correct_answer': answer,
                'question_type': 'basic'
            }
        
        else:
            # Special operations - single operand
            operand = generate_operand(number_of_digits)
            
            if question_type == 'square':
                answer = operand ** 2
                return {
                    'operands': [operand],
                    'operator': '²',
                    'correct_answer': answer,
                    'question_type': 'square'
                }
            elif question_type == 'square_root':
                # Ensure perfect square
                operand = random.randint(1, 20) ** 2
                answer = int(math.sqrt(operand))
                return {
                    'operands': [operand],
                    'operator': '√',
                    'correct_answer': answer,
                    'question_type': 'square_root'
                }
            elif question_type == 'cube':
                answer = operand ** 3
                return {
                    'operands': [operand],
                    'operator': '³',
                    'correct_answer': answer,
                    'question_type': 'cube'
                }
            else:  # cube_root
                # Ensure perfect cube
                operand = random.randint(1, 10) ** 3
                answer = int(round(operand ** (1/3)))
                return {
                    'operands': [operand],
                    'operator': '∛',
                    'correct_answer': answer,
                    'question_type': 'cube_root'
                }


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
            elif requestQuizType == Constants.ORAL_TEST or requestQuizType == Constants.FINAL_TEST:
                curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
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
            if questionFromDb is None:
                return Response({Constants.JSON_MESSAGE: "Invalid QuestionId"}, status=status.HTTP_404_NOT_FOUND)
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
            if questionFromDb is None:
                return Response({Constants.JSON_MESSAGE: "Invalid QuestionId"}, status=status.HTTP_404_NOT_FOUND)
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
            elif requestQuizType == Constants.ORAL_TEST or requestQuizType == Constants.FINAL_TEST:
                curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
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
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            user = UserDetails.objects.filter(userId=userId).first()
            if user.role != Constants.SUB_ADMIN and user.role != Constants.ADMIN:
                return Response({Constants.JSON_MESSAGE: "User is not an admin"}, status=status.HTTP_401_UNAUTHORIZED)
            if user.role == Constants.SUB_ADMIN:
                batchIdDetails = Batch.objects.filter(tag_id=user.tag_id).values()
            else:
                batchIdDetails = Batch.objects.all().values()
            batchIds = []
            for batchId in batchIdDetails:
                batchIds.append(
                    {Constants.BATCH_ID: batchId[Constants.BATCH_ID],
                     Constants.BATCH_NAME: batchId[Constants.BATCH_NAME],
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
                return Response({Constants.JSON_MESSAGE: "Given User is not a Teacher"},
                                status=status.HTTP_403_FORBIDDEN)
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
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            user = UserDetails.objects.filter(userId=userId).first()
            if user.role == Constants.SUB_ADMIN or user.role == Constants.ADMIN:
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
                    'sankeerth@boltabacus.com',
                    [email]
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
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
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


class GetTeachersV2(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            teacherDetails = UserDetails.objects.filter(role=Constants.TEACHER)
            teachers = []
            for teacher in teacherDetails:
                organization = OrganizationTag.objects.filter(tagId=teacher.tag_id).first()
                teachers.append({Constants.USER_ID: teacher.userId,
                                 Constants.FIRST_NAME: teacher.firstName,
                                 Constants.LAST_NAME: teacher.lastName,
                                 Constants.TAG: organization.tagName})
            return Response({"teachers": teachers}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetStudentByName(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            user = UserDetails.objects.filter(userId=userId).first()
            studentName = request.data["name"]
            if user.role != Constants.ADMIN and user.role != Constants.SUB_ADMIN:
                return Response({Constants.JSON_MESSAGE: "User is not an Admin."}, status=status.HTTP_401_UNAUTHORIZED)
            if user.role == Constants.ADMIN:
                students = UserDetails.objects.filter(firstName__istartswith=studentName) | UserDetails.objects.filter(
                    lastName__istartswith=studentName)
            else:
                students = UserDetails.objects.filter(firstName__istartswith=studentName,
                                                      tag_id=user.tag_id) | UserDetails.objects.filter(
                    lastName__istartswith=studentName, tag_id=user.tag_id)
            studentsDetails = []
            for student in students:
                if student.role == Constants.STUDENT:
                    tagName = getTagName(student.tag_id)
                    studentModel = Student.objects.filter(user_id=student.userId).first()
                    studentBatch = Batch.objects.filter(batchId=studentModel.batch_id).first()
                    studentsDetails.append({
                        Constants.USER_ID: student.userId,
                        Constants.FIRST_NAME: student.firstName,
                        Constants.LAST_NAME: student.lastName,
                        Constants.PHONE_NUMBER: student.phoneNumber,
                        Constants.EMAIL: student.email,
                        Constants.TAG: tagName,
                        Constants.BLOCKED: student.blocked,
                        Constants.BATCH_NAME: studentBatch.batchName
                    })
            return Response({"students": studentsDetails}, status=status.HTTP_200_OK )
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetStudentByNameV2(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            user = UserDetails.objects.filter(userId=userId).first()
            studentName = request.data["name"]
            if user.role != Constants.TEACHER:
                return Response({Constants.JSON_MESSAGE: "User is not a Teacher."}, status=status.HTTP_401_UNAUTHORIZED)
            batchStudentIds = getTeacherStudents(userId)
            studentsDetails = []
            tagName = getTagName(user.tag_id)
            for batchId in batchStudentIds:
                studentBatch = Batch.objects.filter(batchId=batchId).first()
                batchName = studentBatch.batchName
                for studentId in batchStudentIds[batchId]:
                    studentDetails = UserDetails.objects.filter(firstName__istartswith=studentName,
                                                                userId=studentId).first()
                    if studentDetails is not None:
                        studentsDetails.append({
                            Constants.USER_ID: studentDetails.userId,
                            Constants.FIRST_NAME: studentDetails.firstName,
                            Constants.LAST_NAME: studentDetails.lastName,
                            Constants.PHONE_NUMBER: studentDetails.phoneNumber,
                            Constants.EMAIL: studentDetails.email,
                            Constants.TAG: tagName,
                            Constants.BATCH_NAME: batchName
                        })

            return Response({"students": studentsDetails}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateBatchTeacher(APIView):


    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            user = UserDetails.objects.filter(userId=userId).first()
            if user.role != Constants.SUB_ADMIN:
                return Response({Constants.JSON_MESSAGE: "User is not a Admin."}, status=status.HTTP_401_UNAUTHORIZED)
            data = request.data
            currentTeacherId = data[Constants.CURRENT_TEACHER_ID]
            futureTeacherId = data[Constants.FUTURE_TEACHER_ID]
            currentTeacher = UserDetails.objects.filter(userId=currentTeacherId).first()
            futureTeacher = UserDetails.objects.filter(userId=futureTeacherId).first()
            batchId = data[Constants.BATCH_ID]

            if futureTeacher is None:
                    return Response({Constants.JSON_MESSAGE: "User you want to assign the batch to does not exist."},
                                    status=status.HTTP_404_NOT_FOUND)
            if currentTeacherId == 0:
                if futureTeacher.role == Constants.TEACHER:
                    return assignTeacherToBatch(batchId, futureTeacherId, currentTeacherId)
                else:
                    return Response({Constants.JSON_MESSAGE: "Given user is not a teacher"},
                                    status=status.HTTP_403_FORBIDDEN)
                
            if currentTeacher is None:
                    return Response({Constants.JSON_MESSAGE: "Given User doesn't exisit."},
                                    status=status.HTTP_404_FORBIDDEN)

            if currentTeacher.role == Constants.TEACHER and futureTeacher.role == Constants.TEACHER:
                return assignTeacherToBatch(batchId, futureTeacherId, currentTeacherId)
            else:
                return Response({Constants.JSON_MESSAGE: "Given user is not a teacher"},
                                status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateStudentBatch(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            
            userDeatils = UserDetails.objects.filter(userId=userId).first()

            if userDeatils.role == Constants.SUB_ADMIN:
                data = request.data
                studentId = data[Constants.USER_ID]
                student = UserDetails.objects.filter(userId=studentId).first()

                if student:
                    if student.role == Constants.STUDENT:
                        if student.tag_id != userDeatils.tag_id:
                            return Response({Constants.JSON_MESSAGE: "This student cannot be moved, please contact the administration"}, 
                                        status=status.HTTP_403_FORBIDDEN)

                        batchId = data[Constants.BATCH_ID]
                        studentBatchDetails = Student.objects.filter(user_id = studentId).first()
                        if batchId == studentBatchDetails.batch_id:
                            return Response({Constants.JSON_MESSAGE: "Student already belongs to this Batch"}, status=status.HTTP_409_CONFLICT)
                        
                        studentBatchDetails.batch_id = batchId
                        studentBatchDetails.save()
                        addProgressIfNeeded(batchId, studentId)
                        
                        return Response({Constants.JSON_MESSAGE: "Student has been reassigned successfully"}, status=status.HTTP_200_OK)

                    else:
                        return Response({Constants.JSON_MESSAGE: "Given user is not a Student"},
                                        status=status.HTTP_403_FORBIDDEN)

                else:
                    return Response({Constants.JSON_MESSAGE: "Given user doesn't exist"},
                                    status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({Constants.JSON_MESSAGE: "User is not an admin"}, status=status.HTTP_401_UNAUTHORIZED)


            pass
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def addProgressIfNeeded( currentBatchId, userId):
    studentDeatils = Student.objects.filter(user_id=userId).first()
    currentBatch = Batch.objects.filter(batchId=currentBatchId).first()
    previousLatestLevel = studentDeatils.latestLevelId
    currentLatestLevel = currentBatch.latestLevelId
    previousLatestClass = studentDeatils.latestClassId
    currentLatestClass = currentBatch.latestClassId
    if ((currentLatestLevel > previousLatestLevel) or
            (currentLatestLevel == previousLatestLevel and previousLatestClass < currentLatestClass)):
        studentDeatils.latestLevelId = currentLatestLevel
        studentDeatils.latestClassId = currentLatestClass
        studentDeatils.save()
        for i in range(previousLatestLevel, currentLatestLevel +1):
            curriculum = Curriculum.objects.filter(levelId=i)
            for quiz in curriculum:
                if ((quiz.levelId < currentLatestLevel) or
                        (quiz.classId <= currentLatestClass and
                         quiz.levelId == currentLatestLevel)):
                    if not Progress.objects.filter(quiz_id=quiz.quizId, user_id=userId).first():
                        progress = Progress.objects.create(
                            quiz_id=quiz.quizId,
                            user_id=userId
                        )
                        progress.save()


class AddStudent(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        requestUserToken = request.headers[Constants.TOKEN_HEADER]
        try:
            userId = IdExtraction(requestUserToken)
            if isinstance(userId, Exception):
                raise Exception(Constants.INVALID_TOKEN_MESSAGE)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
        user = UserDetails.objects.filter(userId=userId).first()
        if user.role == Constants.SUB_ADMIN or user.role == Constants.ADMIN:
            organizationDetails = OrganizationTag.objects.filter(tagId=user.tag_id).first()
            if (organizationDetails.totalNumberOfStudents - organizationDetails.numberOfStudents) <= 0:
                return Response({Constants.JSON_MESSAGE: "The account has reached maximum student it can add. Please "
                                                         "contact the administration to increase the limit."},
                                status=status.HTTP_403_FORBIDDEN)
            return CreateStudentUser(request.data, organizationDetails)
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
                                 Constants.LAST_NAME: student.lastName,
                                 Constants.PHONE_NUMBER: student.phoneNumber,
                                 Constants.EMAIL: student.email,
                                 Constants.BLOCKED: student.blocked})
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


def getTeacherStudents(TeacherUserId):
    teacherBatchIds = list(Teacher.objects.filter(user_id=TeacherUserId).values_list("batchId", flat=True))
    students = {}
    for batchId in teacherBatchIds:
        students[batchId] = getStudentIds(batchId)
    return students


def getStudentIds(batchId):
    studentIdDetails = Student.objects.filter(batch_id=batchId).values_list("user_id", flat=True)
    return list(studentIdDetails)


def getBatchList():
    batchIdDetails = Batch.objects.all().values(Constants.BATCH_ID)
    batchIds = []
    for batchId in batchIdDetails:
        batchIds.append(batchId[Constants.BATCH_ID])
    return set(batchIds)


def CreateStudentUser(data, organizationTag):
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
                role=Constants.STUDENT,
                encryptedPassword=encryptPassword(password),
                created_date=datetime.datetime.now(),
                blocked=False,
                tag_id=organizationTag.tagId
            )
            user.save()

            batchDetails = Batch.objects.filter(batchId=batchId).first()
            latestLevel = batchDetails.latestLevelId
            latestClass = batchDetails.latestClassId
            studentUser = Student.objects.create(
                user=user,
                batch_id=batchId,
                latestLevelId = latestLevel,
                latestClassId = latestClass
            )
            studentUser.save()
            organizationTag.numberOfStudents += 1
            organizationTag.save()
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
                'sankeerth@boltabacus.com',
                [emailId]
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


def assignTeacherToBatch(batchId, futureTeacherId, currentTeacherId):
    batchList = getBatchList()
    if batchId in batchList:
        try:
            teacher = Teacher.objects.filter(user_id=currentTeacherId, batchId=batchId).first()
            if teacher:
                teacher.delete()
            elif currentTeacherId == 0:
                pass
            else:
                return Response({Constants.JSON_MESSAGE: "Given current teacher is not the teacher of the batch."}, status=status.HTTP_403_FORBIDDEN)
            checkBatchTeacher = Teacher.objects.filter(user_id=futureTeacherId, batchId=batchId).first()
            if checkBatchTeacher is not None:
                return Response({Constants.JSON_MESSAGE: "Given user is already the teacher of the batch."}, status=status.HTTP_400_BAD_REQUEST)
            Teacher.objects.create(
                user_id = futureTeacherId,
                batchId = batchId
            )
            return Response({Constants.JSON_MESSAGE: "Teacher has been reassigned successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:

        return Response({Constants.JSON_MESSAGE: "Given batch Id is invalid"},
                        status=status.HTTP_403_FORBIDDEN)


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
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
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
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
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
                    {Constants.BATCH_ID: batch.batchId, Constants.BATCH_NAME: batch.batchName, Constants.LATEST_LEVEL_ID: batch.latestLevelId, Constants.LATEST_CLASS_ID: batch.latestClassId,
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
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
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
            curriculum = Curriculum.objects.filter(levelId=nextLevel, classId__lte=nextClass)
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
            updateStudentLatestClass(nextLevel, nextClass, batch.batchId)
            return Response({Constants.JSON_MESSAGE: Constants.SUCCESS_MESSAGE, "level": nextLevel, "class": nextClass},
                            status=status.HTTP_200_OK)

        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

def updateStudentLatestClass(latestLevelId, latestClassId, batchId):
    studentsDetails = Student.objects.filter(batch_id = batchId)
    for student in  studentsDetails:
        student.latestLevelId = latestLevelId
        student.latestClassId = latestClassId
        student.save()
    return 


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
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            # teacher = UserDetails.objects.filter(userId=requestUserId).first()
            # if teacher is None:
            #     return Response({Constants.JSON_MESSAGE: "User doesn't exist."}, status=status.HTTP_403_FORBIDDEN)
            # if teacher.role != Constants.TEACHER:
            #     return Response({Constants.JSON_MESSAGE: "User is not a teacher."}, status=status.HTTP_403_FORBIDDEN)
            # batchTeacher = Teacher.objects.filter(user_id=requestUserId, batchId=batchId).first()
            # if batchTeacher is None:
            #     return Response({Constants.JSON_MESSAGE: "Teacher is not assigned to the batch."},
            #                     status=status.HTTP_403_FORBIDDEN)
            students = Student.objects.filter(batch_id=batchId)
            studentReports = []
            if classId == 0:
                finalTest = Curriculum.objects.filter(levelId=levelId,
                                            classId=classId,
                                            topicId=0,
                                            quizType=Constants.ORAL_TEST).first()
                
                oralTest = Curriculum.objects.filter(levelId=levelId,
                                            classId=classId,
                                            topicId=0,
                                            quizType=Constants.FINAL_TEST).first()
                
                for student in students:
                    userId = student.user_id
                    user = UserDetails.objects.filter(userId=userId).first()
                    oralTestProgress = Progress.objects.filter(quiz_id=oralTest,
                                                                user_id=userId).first()
                    finalTestProgress = Progress.objects.filter(quiz_id=finalTest,
                                                            user_id=userId).first()
                    if oralTestProgress is None or finalTestProgress is None:
                        return Response(
                            {Constants.JSON_MESSAGE: "Report not found for student " + user.firstName + user.lastName},
                            status=status.HTTP_404_NOT_FOUND)
                    
                    studentReports.append({Constants.USER_ID: user.userId,
                                        Constants.FIRST_NAME: user.firstName,
                                        Constants.LAST_NAME: user.lastName,
                                        "finalTest": finalTestProgress.percentage,
                                        "oralTest": oralTestProgress.percentage})
                
                return Response({"reports": studentReports}, status=status.HTTP_200_OK)
            
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
            import time
            start_time = time.time()
            # Extract token from headers using .get() to avoid KeyError
            auth_token = request.headers.get(Constants.TOKEN_HEADER)
            
            if not auth_token:
                return Response({Constants.JSON_MESSAGE: "Authentication token required"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Decode token to get user
            try:
                payload = jwt.decode(auth_token, Constants.SECRET_KEY, algorithms=['HS256'])
                user_id = payload[Constants.USER_ID]
            except jwt.ExpiredSignatureError:
                return Response({Constants.JSON_MESSAGE: "Token expired"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({Constants.JSON_MESSAGE: "Invalid token"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            resp = getStudentProgress(user_id)
            try:
                took_ms = int((time.time() - start_time) * 1000)
                print(f"[PERF] getStudentProgress user={user_id} took={took_ms}ms")
            except Exception:
                pass
            return resp
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def getStudentProgress(userId):
    try:
        # Optimize queries by using get() where appropriate and prefetching related data
        user = UserDetails.objects.filter(userId=userId).first()
        if user is None:
            return Response({Constants.JSON_MESSAGE: "User doesn't exist."}, status=status.HTTP_404_NOT_FOUND)
        if user.role != Constants.STUDENT:
            return Response({Constants.JSON_MESSAGE: "User is not a Student"}, status=status.HTTP_403_FORBIDDEN)
        student = Student.objects.select_related('batch').filter(user_id=userId).first()
        if student is None:
            return Response({Constants.JSON_MESSAGE: "Student record not found"}, status=status.HTTP_404_NOT_FOUND)
        batchId = student.batch_id
        batch = getattr(student, 'batch', None) or Batch.objects.filter(batchId=batchId).first()
        if batch is None:
            return Response({Constants.JSON_MESSAGE: "Batch not found"}, status=status.HTTP_404_NOT_FOUND)
        # Prefetch curriculum for all quizIds to avoid N+1
        studentProgress = list(Progress.objects.filter(user_id=userId).only('quiz_id', 'percentage', 'time'))
        quiz_ids = [p.quiz_id for p in studentProgress if p.quiz_id is not None]
        curricula = {c.quizId: c for c in Curriculum.objects.filter(quizId__in=quiz_ids).only('quizId', 'levelId', 'classId', 'topicId')}
        levelsProgress = {}
        for progress in studentProgress:
            curriculum = curricula.get(progress.quiz_id)
            if curriculum is None:
                continue  # Skip if curriculum not found
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
                        topicProgressData.append({
                            Constants.TOPIC_ID: topicId,
                            Constants.CLASSWORK: result.get(Constants.CLASSWORK, 0),
                            Constants.CLASSWORK_TIME: result.get(Constants.CLASSWORK_TIME, 0),
                            Constants.HOMEWORK: result.get(Constants.HOMEWORK, 0),
                            Constants.HOMEWORK_TIME: result.get(Constants.HOMEWORK_TIME, 0)
                        })
                if classId != 0:
                    # Safely get test data
                    test_data = topicProgress.get(0, {}) if topicProgress else {}
                    classProgressJson.update({
                        Constants.TEST: test_data.get(Constants.TEST, 0), 
                        "Time": test_data.get(Constants.TEST_TIME, 0)
                    })
                    classProgressJson.update({"topics": topicProgressData})
                    classProgressData.append(classProgressJson)
            
            # Safely get final test and oral test data
            final_test_data = classProgress.get(0, {}).get(0, {}) if classProgress else {}
            levelsProgressJson.update({
                Constants.FINAL_TEST: final_test_data.get(Constants.FINAL_TEST, 0), 
                Constants.FINAL_TEST_TIME: final_test_data.get(Constants.FINAL_TEST_TIME, 0)
            })
            levelsProgressJson.update({
                Constants.ORAL_TEST: final_test_data.get(Constants.ORAL_TEST, 0), 
                Constants.ORAL_TEST_TIME: final_test_data.get(Constants.ORAL_TEST_TIME, 0)
            })
            levelsProgressJson.update({"classes": classProgressData})
            levelsProgressData.append(levelsProgressJson)
        # Sort the data safely
        for classes in levelsProgressData:
            if 'classes' in classes and classes['classes']:
                classes['classes'] = sorted(classes['classes'], key=lambda x: x.get(Constants.CLASS_ID, 0))
                for topics in classes['classes']:
                    if 'topics' in topics and topics['topics']:
                        topics['topics'] = sorted(topics['topics'], key=lambda x: x.get(Constants.TOPIC_ID, 0))

        # Calculate practice stats
        total_sessions = len(studentProgress)
        total_correct = sum(progress.score for progress in studentProgress)  # score represents problems solved
        total_questions = sum(progress.score for progress in studentProgress)  # same as total_correct for now
        total_time = sum(progress.time for progress in studentProgress)  # time in seconds
        
        practice_stats = {
            "totalSessions": total_sessions,
            "totalCorrectAnswers": total_correct,
            "totalQuestions": total_questions,
            "totalTimeSpent": total_time,
            "averageAccuracy": (total_correct / total_questions * 100) if total_questions > 0 else 0,
            "averageTimePerSession": (total_time / total_sessions) if total_sessions > 0 else 0
        }
        
        return Response({
            Constants.FIRST_NAME: user.firstName,
            Constants.LAST_NAME: user.lastName,
            Constants.BATCH_NAME: batch.batchName,
            "levels": levelsProgressData,
            "practiceStats": practice_stats
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def getClassIds(levelId):
    classIds = set()
    classes = TopicDetails.objects.filter(levelId=levelId)
    for eachClass in classes:
        classIds.add(eachClass.classId)
    classIds.add(0)
    return classIds


def getNextClass(levelId, classId, tag_id):
    organizationsDetails = OrganizationTag.objects.filter(tagId=tag_id).first()
    maxLevelAllowed = organizationsDetails.maxLevel
    maxClassAllowed = organizationsDetails.maxClass
    if classId > 12 or classId < 0:
        return -2, -2
    if levelId > 10 or levelId < 0:
        return -3, -3
    if levelId > maxLevelAllowed or (levelId == maxLevelAllowed and classId >= maxClassAllowed):
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
            elif requestQuizType == Constants.ORAL_TEST or requestQuizType == Constants.FINAL_TEST:
                curriculumDetails = Curriculum.objects.filter(levelId=requestLevelId,
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
        try:
            data = request.data
            email = data[Constants.EMAIL].lower()
            user = UserDetails.objects.filter(email=email).first()
            if user is not None:

                organization = OrganizationTag.objects.filter(tagId=user.tag_id).first()
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

        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
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
        'sankeerth@boltabacus.com',
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
                'sankeerth@boltabacus.com',
                [email]
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
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
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
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
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
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
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
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
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
                        {Constants.JSON_MESSAGE: "Please note that the account is currently exceeding the maximum "
                                                 "student limit. Kindly contact the administration to discuss "
                                                 "potential adjustments"},
                        status=status.HTTP_403_FORBIDDEN)
                batchList = getBatchList()
                if batchId not in batchList:
                    return Response({Constants.JSON_MESSAGE: "Given batch Id is invalid"},
                                    status=status.HTTP_404_NOT_FOUND)
                existingStudents = set()
                nonExistingStudents = []
                studentsNotAdded = []
                multipleEntries = set()
                studentEmails = set()
                for i in range(len(students)):
                    studentEmailId = students[i][Constants.EMAIL]
                    tempUserObject = UserDetails.objects.filter(email=studentEmailId).first()
                    if tempUserObject is not None:
                        existingStudents.add(studentEmailId)
                    else:
                        if studentEmailId not in studentEmails:
                            nonExistingStudents.append(i)
                            studentEmails.add(studentEmailId)
                        else:
                            multipleEntries.add(studentEmailId)
                for i in nonExistingStudents:
                    try:
                        studentData = {
                            Constants.FIRST_NAME: students[i][Constants.FIRST_NAME],
                            Constants.LAST_NAME: students[i][Constants.LAST_NAME],
                            Constants.PHONE_NUMBER: students[i][Constants.PHONE_NUMBER],
                            Constants.EMAIL: students[i][Constants.EMAIL],
                            Constants.BATCH_ID: batchId
                        }
                        studentResponse = CreateStudentUser(studentData, organizationDetails)
                        if studentResponse.status_code != 200:
                            studentsNotAdded.append(students[i][Constants.EMAIL])
                    except Exception as e:
                        studentsNotAdded.append(students[i][Constants.EMAIL])

                if len(students) == len(nonExistingStudents):
                    return Response({Constants.JSON_MESSAGE: "All the students have been successfully added."},
                                    status=status.HTTP_200_OK)
                else:
                    return Response(
                        {Constants.JSON_MESSAGE: "Partial Success",
                         "NumberOfStudentsAdded": len(nonExistingStudents),
                         "ExistingStudents": list(existingStudents),
                         "UndefinedError": studentsNotAdded,
                         "MultipleEntries": list(multipleEntries)},
                        status=status.HTTP_206_PARTIAL_CONTENT)

            else:
                return Response({Constants.JSON_MESSAGE: "User is not an admin"}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class GetBatchTeacher(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        try:

            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            user = UserDetails.objects.filter(userId=userId).first()
            role = user.role
            if role == Constants.SUB_ADMIN:
                data = request.data
                batchId = data[Constants.BATCH_ID]
                teacherDeatils = []
                teachers = Teacher.objects.filter(batchId=batchId)
                for teacher in teachers:
                    user = UserDetails.objects.filter(userId=teacher.user_id).first()
                    teacherDeatils.append({Constants.FIRST_NAME: user.firstName, Constants.LAST_NAME: user.lastName,Constants.USER_ID: user.userId})
                return Response({"teachers": teacherDeatils}, status=status.HTTP_200_OK)
            else:
                return Response({Constants.JSON_MESSAGE: "User is not an admin"}, status=status.HTTP_401_UNAUTHORIZED)
                
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AccountDeactivation(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:

            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            
            userDeatils = UserDetails.objects.filter(userId=userId).first()
            if userDeatils.role == Constants.ADMIN or userDeatils.role == Constants.SUB_ADMIN:

                deactivationUserId = request.data[Constants.USER_ID]
                deactivationUserDetails = UserDetails.objects.filter(userId=deactivationUserId).first()
                if deactivationUserDetails is None:
                    return Response({Constants.JSON_MESSAGE: "Given user is Invalid."}, status=status.HTTP_400_BAD_REQUEST)

                if userDeatils.role == Constants.SUB_ADMIN:
                    if deactivationUserDetails.tag_id != userDeatils.tag_id:
                        return Response({Constants.JSON_MESSAGE: "You cannot deactivate the account, please contact the administration"}, 
                                        status=status.HTTP_403_FORBIDDEN)
                if deactivationUserDetails.blocked == True:
                    return Response({Constants.JSON_MESSAGE: "Given user is already deactivated."}, status=status.HTTP_409_CONFLICT)
                deactivationUserDetails.blocked = True
                deactivationUserDetails.blockedTimestamp = datetime.datetime.today()
                deactivationUserDetails.save()
                return Response({Constants.JSON_MESSAGE: "User has been deactivated successfully."}, status=status.HTTP_200_OK)
            else:
                return Response({Constants.JSON_MESSAGE: "User is not an admin"}, status=status.HTTP_401_UNAUTHORIZED)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class AccountDelete(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            
            userDeatils = UserDetails.objects.filter(userId=userId).first()

            if userDeatils is None:
                return Response({Constants.JSON_MESSAGE: "Invalid user."}, status=status.HTTP_400_BAD_REQUEST)
            if userDeatils.role == Constants.STUDENT:
                userDeatils.delete()
                return Response({Constants.JSON_MESSAGE: "User is deleted successfully."}, status=status.HTTP_200_OK)
            
            if userDeatils.role == Constants.SUB_ADMIN or userDeatils.role == Constants.ADMIN:
                deletionUserId = request.data['userId']
                deletionUserDetails = UserDetails.objects.filter(userId=deletionUserId).first()

                if deletionUserDetails is None:
                    return Response({Constants.JSON_MESSAGE: "Given user is Invalid."}, status=status.HTTP_400_BAD_REQUEST)

                if deletionUserDetails.role != Constants.TEACHER:
                    return Response({Constants.JSON_MESSAGE: "Given user is not a Teacher"}, status=status.HTTP_401_UNAUTHORIZED)
                
                else:
                    if userDeatils.role == Constants.SUB_ADMIN:
                        if deletionUserDetails.tag_id != userDeatils.tag_id:
                            return Response({Constants.JSON_MESSAGE: "You cannot delete the account, please contact the administration"}, 
                                            status=status.HTTP_403_FORBIDDEN)
                    
                    deletionUserDetails.delete()
                    return Response({Constants.JSON_MESSAGE: "User is deleted successfully."}, status=status.HTTP_200_OK)

            return Response({Constants.JSON_MESSAGE: "You cannot delete the account, please contact the administration"}, 
                            status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



def getTagName(tagId):
    organization = OrganizationTag.objects.filter(tagId=tagId).first()
    return organization.tagName


class AccountReactivate(APIView):
    permission_classes = [AllowAny]
    def post(self, request):

        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            
            userDeatils = UserDetails.objects.filter(userId=userId).first()
            if userDeatils.role == Constants.ADMIN or userDeatils.role == Constants.SUB_ADMIN:

                activationUserId = request.data[Constants.USER_ID]
                activationUserDetails = UserDetails.objects.filter(userId=activationUserId).first()
                if activationUserDetails is None:
                    return Response({Constants.JSON_MESSAGE: "Invalid user."}, status=status.HTTP_400_BAD_REQUEST)

                if userDeatils.role == Constants.SUB_ADMIN:
                    if activationUserDetails.tag_id != userDeatils.tag_id:
                        return Response({Constants.JSON_MESSAGE: "You cannot activate the account, please contact the administration"}, 
                                        status=status.HTTP_403_FORBIDDEN)
                if activationUserDetails.blocked == False:
                    return Response({Constants.JSON_MESSAGE: "User is already activated."}, status=status.HTTP_409_CONFLICT)
                activationUserDetails.blocked = False
                activationUserDetails.blockedTimestamp = datetime.datetime.today()
                activationUserDetails.save()
                return Response({Constants.JSON_MESSAGE: "User has been activated successfully."}, status=status.HTTP_200_OK)
            else:
                return Response({Constants.JSON_MESSAGE: "User is not an admin"}, status=status.HTTP_401_UNAUTHORIZED)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetStudentBatchDetails(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            
            userDeatils = UserDetails.objects.filter(userId=userId).first()
            if userDeatils is None:
                    return Response({Constants.JSON_MESSAGE: "Invalid user."}, status=status.HTTP_400_BAD_REQUEST)
               
            if userDeatils.role == Constants.SUB_ADMIN:
                studentId = request.data[Constants.USER_ID]
                studentDetails = UserDetails.objects.filter(userId = studentId).first()
                if studentDetails is None:
                    return Response({Constants.JSON_MESSAGE: "Given user is Invalid."}, status=status.HTTP_400_BAD_REQUEST)
                if studentDetails.role != Constants.STUDENT:
                    return Response({Constants.JSON_MESSAGE: "Given user is not a Student."}, status=status.HTTP_400_BAD_REQUEST)

                if studentDetails.tag_id != userDeatils.tag_id:
                    return Response({Constants.JSON_MESSAGE: "This student cannot be viwed, please contact the administration"}, 
                            status=status.HTTP_403_FORBIDDEN)
                batchDetails = Student.objects.filter(user_id=studentId).first()
                if batchDetails is None:
                    return Response({Constants.JSON_MESSAGE: "Given user is Invalid."}, status=status.HTTP_400_BAD_REQUEST)
                studentBatchDetails = Batch.objects.filter(batchId=batchDetails.batch_id).first()
                if studentBatchDetails is None:
                    return Response({Constants.JSON_MESSAGE: "Given user is Invalid."}, status=status.HTTP_400_BAD_REQUEST)
                return Response({
                    Constants.FIRST_NAME: studentDetails.firstName,
                    Constants.LAST_NAME: studentDetails.lastName,
                    Constants.EMAIL: studentDetails.email,
                    Constants.BATCH_ID: studentBatchDetails.batchId,
                    Constants.BATCH_NAME: studentBatchDetails.batchName
                }, status=status.HTTP_200_OK)
            else:
                return Response({Constants.JSON_MESSAGE: "User is not an admin"}, status=status.HTTP_401_UNAUTHORIZED)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class SubmitPracticeQuestions(APIView):

    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            user = UserDetails.objects.filter(userId=userId).first()
            data = request.data
            practiceType = data[Constants.PRACTICE_TYPE]
            operation = data[Constants.OPERATION]
            numberOfDigits = data[Constants.NUMBER_OF_DIGITS]
            numberOfQuestions = data[Constants.NUMBER_OF_QUESTIONS]
            numberOfRows = data[Constants.NUMBER_OF_ROWS]
            zigZag = data[Constants.ZIG_ZAG]
            includeSubtraction = data[Constants.INCLUDE_SUBTRACTION]
            persistNumberOfDigits = data[Constants.PERSIST_NUMBER_OF_DIGITS]
            score = data[Constants.SCORE]
            totalTime = data[Constants.TOTAL_TIME]
            averageTime = data[Constants.AVERAGE_TIME]  
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User doesn't exist."}, status=status.HTTP_404_NOT_FOUND)
            if not ifPracticeQuestionsAlreadyExists(data, userId):
                PracticeQuestions.objects.create(
                    user_id = userId,
                    practiceType = practiceType,
                    operation = operation,
                    numberOfDigits = numberOfDigits,
                    numberOfQuestions = numberOfQuestions,
                    numberOfRows = numberOfRows,
                    zigZag = zigZag,
                    includeSubtraction = includeSubtraction,
                    persistNumberOfDigits = persistNumberOfDigits,
                    score = score,
                    totalTime = totalTime,
                    averageTime = averageTime
                )
                return Response({Constants.JSON_MESSAGE: "Practice Attempt stored Successfully"}, status=status.HTTP_200_OK)
            return Response({Constants.JSON_MESSAGE: "Practice Attempt already stored"}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetStudentPracticeQuestions(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            userId = data[Constants.USER_ID]
            return getStudentPracticeStatistics(userId)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetStudentPracticeQuestionsStudent(APIView):
    permission_classes = [AllowAny]

    def post(self, request):

        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            return getStudentPracticeStatistics(userId)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class DeleteStudentPracticeQuestion(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            user = UserDetails.objects.filter(userId=userId).first()
            if user.role != Constants.SUB_ADMIN and user.role != Constants.ADMIN:
                return Response({Constants.JSON_MESSAGE: "User is not an admin"}, status=status.HTTP_401_UNAUTHORIZED)
            

            requestPracticeQuestionDeletionId = request.data[Constants.PRACTICE_QUESTION_ID]
            practiceQuestion = PracticeQuestions.objects.filter(practiceQuestionId=requestPracticeQuestionDeletionId).first()
            if practiceQuestion is None:
                return Response({Constants.JSON_MESSAGE: "Question Already Deleted or doesnt exist"}, status=status.HTTP_400_BAD_REQUEST)
            student = practiceQuestion.user 
            
            if user.role == Constants.SUB_ADMIN:
                if student.tag_id != userId.tag_id:
                    return Response({Constants.JSON_MESSAGE: "You cannot delete this practice question, please contact the administration"}, 
                                    status=status.HTTP_403_FORBIDDEN)
                
            practiceQuestion.delete()
            return Response({Constants.JSON_MESSAGE: "Deleted the pratice question"}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteQuestion(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            print("DeleteQuestion: Request received")
            print("DeleteQuestion: Request data:", request.data)
            print("DeleteQuestion: Request headers:", request.headers)
            
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                print("DeleteQuestion: Token extraction error:", repr(e))
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            
            print("DeleteQuestion: User ID:", userId)
            user = UserDetails.objects.filter(userId=userId).first()
            if user is None:
                print("DeleteQuestion: User not found")
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            if user.role != Constants.SUB_ADMIN and user.role != Constants.ADMIN:
                print("DeleteQuestion: User is not admin, role:", user.role)
                return Response({Constants.JSON_MESSAGE: "User is not an admin"}, status=status.HTTP_401_UNAUTHORIZED)
            
            requestQuestionId = request.data[Constants.QUESTION_ID]
            print("DeleteQuestion: Question ID to delete:", requestQuestionId)
            
            question = QuizQuestions.objects.filter(questionId=requestQuestionId).first()
            if question is None:
                print("DeleteQuestion: Question not found")
                return Response({Constants.JSON_MESSAGE: "Question already deleted or doesn't exist"}, status=status.HTTP_400_BAD_REQUEST)
            
            print("DeleteQuestion: Question found, deleting...")
            question.delete()
            print("DeleteQuestion: Question deleted successfully")
            return Response({Constants.JSON_MESSAGE: "Question deleted successfully"}, status=status.HTTP_200_OK)
        
        except Exception as e:
            print("DeleteQuestion: Exception occurred:", repr(e))
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



def getStudentPracticeStatistics(userId):
    try:
        user = UserDetails.objects.filter(userId=userId).first()
        if user is None:
            return Response({Constants.JSON_MESSAGE: "User doesn't exist."}, status=status.HTTP_404_NOT_FOUND)
        if user.role != Constants.STUDENT:
            return Response({Constants.JSON_MESSAGE: "User is not a Student"}, status=status.HTTP_403_FORBIDDEN)
        practiceQuestions = PracticeQuestions.objects.filter(user_id=userId).values(
                Constants.PRACTICE_QUESTION_ID,
                Constants.PRACTICE_TYPE,
                Constants.OPERATION,
                Constants.NUMBER_OF_DIGITS,
                Constants.NUMBER_OF_QUESTIONS,
                Constants.NUMBER_OF_ROWS,
                Constants.ZIG_ZAG,
                Constants.INCLUDE_SUBTRACTION,
                Constants.PERSIST_NUMBER_OF_DIGITS,
                Constants.SCORE,
                Constants.TOTAL_TIME,
                Constants.AVERAGE_TIME
            ) 
        return Response({"practiceQuestions": practiceQuestions})
            

    except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def ifPracticeQuestionsAlreadyExists(data, userId):
    practiceQuestions =  PracticeQuestions.objects.filter(
        user_id=userId,
        practiceType=data[Constants.PRACTICE_TYPE],
        operation=data[Constants.OPERATION],
        numberOfDigits=data[Constants.NUMBER_OF_DIGITS],
        numberOfQuestions=data[Constants.NUMBER_OF_QUESTIONS],
        numberOfRows=data[Constants.NUMBER_OF_ROWS],
        zigZag=data[Constants.ZIG_ZAG],
        includeSubtraction=data[Constants.INCLUDE_SUBTRACTION],
        persistNumberOfDigits=data[Constants.PERSIST_NUMBER_OF_DIGITS],
        score=data[Constants.SCORE],
        totalTime=data[Constants.TOTAL_TIME],
        averageTime=data[Constants.AVERAGE_TIME]).first()
    if practiceQuestions is None:
        return False
    return True
def temp():
    print()

# PVP and Experience API Views
class CreatePVPRoom(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            
            user = UserDetails.objects.filter(userId=userId).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            if user.role != Constants.STUDENT:
                return Response({Constants.JSON_MESSAGE: "Only students can create PVP rooms"}, status=status.HTTP_403_FORBIDDEN)
            
            # Generate unique room code
            import random
            import string
            
            def generate_room_code():
                while True:
                    # Generate 6-digit numeric code
                    code = ''.join(random.choices(string.digits, k=6))
                    if not PVPRoom.objects.filter(room_id=code).exists():
                        return code
            
            room_code = generate_room_code()
            
            # Create room
            room = PVPRoom.objects.create(
                room_id=room_code,
                creator=user,
                max_players=request.data.get('max_players', 2),
                number_of_questions=request.data.get('number_of_questions', 10),
                time_per_question=request.data.get('time_per_question', 30),
                level_id=request.data.get('level_id', 1),
                class_id=request.data.get('class_id', 1),
                topic_id=request.data.get('topic_id', 1)
            )
            
            # Add creator as first player
            PVPRoomPlayer.objects.create(
                room=room,
                player=user,
                status='joined'
            )
            
            room.current_players = 1
            room.save()
            
            return Response({
                'success': True,
                'room_id': room.room_id,
                'message': 'Room created successfully'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class JoinPVPRoom(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            
            user = UserDetails.objects.filter(userId=userId).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            if user.role != Constants.STUDENT:
                return Response({Constants.JSON_MESSAGE: "Only students can join PVP rooms"}, status=status.HTTP_403_FORBIDDEN)
            
            room_id = request.data.get('room_id')
            if not room_id:
                return Response({Constants.JSON_MESSAGE: "Room ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            room = PVPRoom.objects.filter(room_id=room_id).first()
            if not room:
                return Response({Constants.JSON_MESSAGE: "Room not found"}, status=status.HTTP_404_NOT_FOUND)
            
            if room.status != 'waiting':
                return Response({Constants.JSON_MESSAGE: "Room is not accepting players"}, status=status.HTTP_400_BAD_REQUEST)
            
            if room.current_players >= room.max_players:
                return Response({Constants.JSON_MESSAGE: "Room is full"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if player already in room
            existing_player = PVPRoomPlayer.objects.filter(room=room, player=user).first()
            if existing_player:
                return Response({Constants.JSON_MESSAGE: "You are already in this room"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Add player to room
            PVPRoomPlayer.objects.create(
                room=room,
                player=user,
                status='joined'
            )
            
            room.current_players += 1
            room.save()
            
            return Response({
                'success': True,
                'room_id': room.room_id,
                'message': 'Joined room successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetPVPRoomDetails(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            
            user = UserDetails.objects.filter(userId=userId).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            room_id = request.data.get('room_id')
            if not room_id:
                return Response({Constants.JSON_MESSAGE: "Room ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            room = PVPRoom.objects.filter(room_id=room_id).first()
            if not room:
                return Response({Constants.JSON_MESSAGE: "Room not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Get players in room
            players = []
            for player in room.players.all():
                players.append({
                    'user_id': player.player.userId,
                    'name': f"{player.player.firstName} {player.player.lastName}",
                    'status': player.status,
                    'is_ready': player.is_ready,
                    'score': player.score
                })
            
            room_data = {
                'room_id': room.room_id,
                'creator_id': room.creator.userId,
                'creator_name': f"{room.creator.firstName} {room.creator.lastName}",
                'status': room.status,
                'max_players': room.max_players,
                'current_players': room.current_players,
                'number_of_questions': room.number_of_questions,
                'time_per_question': room.time_per_question,
                'level_id': room.level_id,
                'class_id': room.class_id,
                'topic_id': room.topic_id,
                'created_at': room.created_at,
                'players': players
            }
            
            return Response({
                'success': True,
                'data': room_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetUserExperience(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # Extract token from headers using .get() to avoid KeyError
            auth_token = request.headers.get(Constants.TOKEN_HEADER)
            
            if not auth_token:
                return Response({Constants.JSON_MESSAGE: "Authentication token required"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Decode token to get user
            try:
                payload = jwt.decode(auth_token, Constants.SECRET_KEY, algorithms=['HS256'])
                user_id = payload[Constants.USER_ID]
            except jwt.ExpiredSignatureError:
                return Response({Constants.JSON_MESSAGE: "Token expired"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({Constants.JSON_MESSAGE: "Invalid token"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            user = UserDetails.objects.filter(userId=user_id).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            user_exp, created = UserExperience.objects.get_or_create(
                user=user,
                defaults={'experience_points': 0, 'level': 1}
            )
            
            # Calculate XP to next level based on new system
            if user_exp.experience_points <= 90:
                xp_to_next = 100 - user_exp.experience_points
            else:
                xp_to_next = 100 - ((user_exp.experience_points - 90) % 100)
            
            exp_data = {
                'user_id': user.userId,
                'experience_points': user_exp.experience_points,
                'level': user_exp.level,
                'xp_to_next_level': xp_to_next
            }
            
            return Response({
                'success': True,
                'data': exp_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetCommunityStats(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # Get total active players (users with XP > 0)
            active_players = UserExperience.objects.filter(experience_points__gt=0).count()
            
            # Get unique countries (assuming we have a country field in UserDetails)
            countries = UserDetails.objects.values('country').distinct().exclude(country__isnull=True).exclude(country='').count()
            
            # Get problems solved today (this would need to be tracked in a separate model)
            # For now, we'll use a placeholder calculation
            from datetime import date
            today = date.today()
            problems_solved_today = 0  # This would need to be calculated from actual practice data
            
            # Get average accuracy (this would need to be calculated from practice results)
            # For now, we'll use a placeholder
            average_accuracy = 85.0  # This would need to be calculated from actual data
            
            stats_data = {
                'active_players': active_players,
                'countries': countries,
                'problems_solved_today': problems_solved_today,
                'average_accuracy': average_accuracy
            }
            
            return Response({
                'success': True,
                'data': stats_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetUserStats(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # Extract token from headers
            auth_token = request.headers.get(Constants.TOKEN_HEADER)
            
            if not auth_token:
                return Response({Constants.JSON_MESSAGE: "Authentication token required"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Decode token to get user
            try:
                payload = jwt.decode(auth_token, Constants.SECRET_KEY, algorithms=['HS256'])
                user_id = payload[Constants.USER_ID]
            except jwt.ExpiredSignatureError:
                return Response({Constants.JSON_MESSAGE: "Token expired"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({Constants.JSON_MESSAGE: "Invalid token"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            user = UserDetails.objects.filter(userId=user_id).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            user_exp, created = UserExperience.objects.get_or_create(
                user=user,
                defaults={'experience_points': 0, 'level': 1}
            )
            
            # Calculate user's rank among all users with XP > 0
            users_with_xp = UserExperience.objects.filter(experience_points__gt=0).order_by('-experience_points')
            user_rank = 0
            for i, exp in enumerate(users_with_xp):
                if exp.user == user:
                    user_rank = i + 1
                    break
            
            # Calculate current level based on experience points
            if user_exp.experience_points <= 90:
                current_level = 1
                next_level_xp = 100 - user_exp.experience_points
            else:
                current_level = ((user_exp.experience_points - 90) // 100) + 2
                next_level_xp = 100 - ((user_exp.experience_points - 90) % 100)
            
            # Update the user's level if it's different
            if user_exp.level != current_level:
                user_exp.level = current_level
                user_exp.save()
            
            stats_data = {
                'total_xp': user_exp.experience_points,
                'level': current_level,
                'rank': user_rank,
                'total_players': users_with_xp.count(),
                'next_level_xp': next_level_xp
            }
            
            return Response({
                'success': True,
                'data': stats_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetUserDetails(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # Extract token from headers using .get() to avoid KeyError
            auth_token = request.headers.get(Constants.TOKEN_HEADER)
            
            if not auth_token:
                return Response({Constants.JSON_MESSAGE: "Authentication token required"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Decode token to get user
            try:
                payload = jwt.decode(auth_token, Constants.SECRET_KEY, algorithms=['HS256'])
                user_id = payload[Constants.USER_ID]
            except jwt.ExpiredSignatureError:
                return Response({Constants.JSON_MESSAGE: "Token expired"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({Constants.JSON_MESSAGE: "Invalid token"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            user = UserDetails.objects.filter(userId=user_id).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            user_data = {
                'id': user.userId,
                'firstName': user.firstName,
                'lastName': user.lastName,
                'email': user.email,
                'phone': user.phoneNumber,  # Fahad: use phoneNumber instead of phone as received from the UserDetails model.
                'organizationName': user.tag.organizationName if user.tag else 'Unknown',
                'role': user.role
            }
            
            return Response({
                'success': True,
                'data': user_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetPVPGameQuestions(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            
            user = UserDetails.objects.filter(userId=userId).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            room_id = request.data.get('room_id')
            if not room_id:
                return Response({Constants.JSON_MESSAGE: "Room ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            room = PVPRoom.objects.filter(room_id=room_id).first()
            if not room:
                return Response({Constants.JSON_MESSAGE: "Room not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if room is active
            if room.status != 'active':
                return Response({Constants.JSON_MESSAGE: "Game is not active"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get game session
            game_session = PVPGameSession.objects.filter(room=room, is_active=True).first()
            if not game_session:
                return Response({Constants.JSON_MESSAGE: "Game session not found"}, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'success': True,
                'data': {
                    'questions': game_session.questions_data,
                    'total_questions': room.number_of_questions,
                    'time_per_question': room.time_per_question
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetWeeklyStats(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # Extract token from headers
            auth_token = request.headers.get(Constants.TOKEN_HEADER)
            
            if not auth_token:
                return Response({Constants.JSON_MESSAGE: "Authentication token required"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Decode token to get user
            try:
                payload = jwt.decode(auth_token, Constants.SECRET_KEY, algorithms=['HS256'])
                user_id = payload[Constants.USER_ID]
            except jwt.ExpiredSignatureError:
                return Response({Constants.JSON_MESSAGE: "Token expired"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({Constants.JSON_MESSAGE: "Invalid token"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            user = UserDetails.objects.filter(userId=user_id).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Calculate weekly stats (last 7 days)
            from datetime import datetime, timedelta
            week_ago = datetime.now() - timedelta(days=7)
            
            # Get practice sessions from last week
            weekly_sessions = Progress.objects.filter(
                user=user,
                created_at__gte=week_ago
            ).count()
            
            # Calculate accuracy (correct answers / total attempts)
            total_attempts = Progress.objects.filter(
                user=user,
                created_at__gte=week_ago
            ).aggregate(total=models.Sum('totalQuestions'))['total'] or 0
            
            total_correct = Progress.objects.filter(
                user=user,
                created_at__gte=week_ago
            ).aggregate(total=models.Sum('correctAnswers'))['total'] or 0
            
            accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
            
            # Calculate time spent (in seconds)
            time_spent = Progress.objects.filter(
                user=user,
                created_at__gte=week_ago
            ).aggregate(total=models.Sum('timeSpent'))['total'] or 0
            
            # Convert to hours and minutes
            hours = int(time_spent // 3600)
            minutes = int((time_spent % 3600) // 60)
            
            stats_data = {
                'sessions': weekly_sessions,
                'accuracy': round(accuracy, 1),
                'time_spent_hours': hours,
                'time_spent_minutes': minutes,
                'time_spent_formatted': f"{hours}h {minutes}m"
            }
            
            return Response({
                'success': True,
                'data': stats_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetUserTodoList(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # Extract token from headers
            auth_token = request.headers.get(Constants.TOKEN_HEADER)
            
            if not auth_token:
                return Response({Constants.JSON_MESSAGE: "Authentication token required"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Decode token to get user
            try:
                payload = jwt.decode(auth_token, Constants.SECRET_KEY, algorithms=['HS256'])
                user_id = payload[Constants.USER_ID]
            except jwt.ExpiredSignatureError:
                return Response({Constants.JSON_MESSAGE: "Token expired"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({Constants.JSON_MESSAGE: "Invalid token"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            user = UserDetails.objects.filter(userId=user_id).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Generate personalized todo list based on user progress
            todos = []
            
            # Check if user has completed any practice sessions
            practice_sessions = Progress.objects.filter(user=user).count()
            if practice_sessions == 0:
                todos.append({
                    'id': 'first_practice',
                    'title': 'Complete your first practice session',
                    'description': 'Start your learning journey with a practice session',
                    'completed': False,
                    'priority': 'high',
                    'type': 'practice'
                })
            elif practice_sessions < 5:
                todos.append({
                    'id': 'complete_5_sessions',
                    'title': f'Complete {5 - practice_sessions} more practice sessions',
                    'description': 'Build consistency with regular practice',
                    'completed': False,
                    'priority': 'medium',
                    'type': 'practice'
                })
            
            # Check streak
            try:
                user_streak, _ = UserStreak.get_or_create_streak(user)
                if user_streak.current_streak == 0:
                    todos.append({
                        'id': 'start_streak',
                        'title': 'Start your learning streak',
                        'description': 'Practice daily to build a streak',
                        'completed': False,
                        'priority': 'high',
                        'type': 'streak'
                    })
                elif user_streak.current_streak < 7:
                    todos.append({
                        'id': 'week_streak',
                        'title': f'Maintain streak for {7 - user_streak.current_streak} more days',
                        'description': 'Reach a 7-day streak milestone',
                        'completed': False,
                        'priority': 'medium',
                        'type': 'streak'
                    })
            except:
                pass
            
            # Check experience level
            try:
                user_exp, _ = UserExperience.objects.get_or_create(
                    user=user,
                    defaults={'experience_points': 0, 'level': 1}
                )
                if user_exp.level < 5:
                    todos.append({
                        'id': 'reach_level_5',
                        'title': f'Reach Level 5 (Current: Level {user_exp.level})',
                        'description': 'Gain more experience points to level up',
                        'completed': False,
                        'priority': 'medium',
                        'type': 'level'
                    })
            except:
                pass
            
            # Check if user has tried PVP
            pvp_games = PVPGameResult.objects.filter(
                models.Q(player1=user) | models.Q(player2=user)
            ).count()
            if pvp_games == 0:
                todos.append({
                    'id': 'try_pvp',
                    'title': 'Try PVP mode',
                    'description': 'Challenge other players in multiplayer battles',
                    'completed': False,
                    'priority': 'low',
                    'type': 'pvp'
                })
            
            # Add some completed todos for motivation
            if practice_sessions > 0:
                todos.append({
                    'id': 'first_practice_completed',
                    'title': 'Complete your first practice session',
                    'description': 'Great start to your learning journey!',
                    'completed': True,
                    'priority': 'high',
                    'type': 'practice'
                })
            
            if practice_sessions >= 5:
                todos.append({
                    'id': 'complete_5_sessions_completed',
                    'title': 'Complete 5 practice sessions',
                    'description': 'Excellent consistency!',
                    'completed': True,
                    'priority': 'medium',
                    'type': 'practice'
                })
            
            # Add personal goals from database
            from .models import PersonalGoal
            personal_goals = PersonalGoal.objects.filter(user=user).order_by('-created_at')
            for goal in personal_goals:
                todos.append({
                    'id': str(goal.id),
                    'title': goal.title,
                    'description': goal.description or '',
                    'completed': goal.completed,
                    'priority': goal.priority,
                    'type': goal.goal_type
                })
            
            return Response({
                'success': True,
                'data': {
                    'todos': todos,
                    'total_todos': len(todos),
                    'completed_todos': len([t for t in todos if t['completed']]),
                    'pending_todos': len([t for t in todos if not t['completed']])
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddPersonalGoal(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # Extract token from headers
            auth_token = request.headers.get(Constants.TOKEN_HEADER)
            
            if not auth_token:
                return Response({Constants.JSON_MESSAGE: "Authentication token required"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Decode token to get user
            try:
                payload = jwt.decode(auth_token, Constants.SECRET_KEY, algorithms=['HS256'])
                user_id = payload[Constants.USER_ID]
            except jwt.ExpiredSignatureError:
                return Response({Constants.JSON_MESSAGE: "Token expired"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({Constants.JSON_MESSAGE: "Invalid token"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            user = UserDetails.objects.filter(userId=user_id).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Get goal data from request
            goal_title = request.data.get('title', '').strip()
            goal_description = request.data.get('description', '').strip()
            
            if not goal_title:
                return Response({Constants.JSON_MESSAGE: "Goal title is required"}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            # Create personal goal using PersonalGoal model
            from .models import PersonalGoal
            
            personal_goal = PersonalGoal.objects.create(
                user=user,
                title=goal_title,
                description=goal_description,
                priority='medium',
                goal_type='personal'
            )
            
            return Response({
                'success': True,
                'message': 'Personal goal added successfully',
                'data': {
                    'id': str(personal_goal.id),
                    'title': personal_goal.title,
                    'description': personal_goal.description,
                    'completed': personal_goal.completed,
                    'priority': personal_goal.priority,
                    'type': personal_goal.goal_type
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RemovePersonalGoal(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # Extract token from headers
            auth_token = request.headers.get(Constants.TOKEN_HEADER)
            
            if not auth_token:
                return Response({Constants.JSON_MESSAGE: "Authentication token required"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Decode token to get user
            try:
                payload = jwt.decode(auth_token, Constants.SECRET_KEY, algorithms=['HS256'])
                user_id = payload[Constants.USER_ID]
            except jwt.ExpiredSignatureError:
                return Response({Constants.JSON_MESSAGE: "Token expired"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({Constants.JSON_MESSAGE: "Invalid token"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            user = UserDetails.objects.filter(userId=user_id).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Get goal ID from request
            goal_id = request.data.get('goal_id', '').strip()
            
            if not goal_id:
                return Response({Constants.JSON_MESSAGE: "Goal ID is required"}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            # Remove personal goal using PersonalGoal model
            from .models import PersonalGoal
            
            try:
                personal_goal = PersonalGoal.objects.get(id=goal_id, user=user)
                personal_goal.delete()
                
                return Response({
                    'success': True,
                    'message': 'Personal goal removed successfully'
                }, status=status.HTTP_200_OK)
            except PersonalGoal.DoesNotExist:
                return Response({Constants.JSON_MESSAGE: "Personal goal not found"}, 
                              status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetPVPGameResult(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # Extract token from headers using .get() to avoid KeyError
            auth_token = request.headers.get(Constants.TOKEN_HEADER)
            
            if not auth_token:
                return Response({Constants.JSON_MESSAGE: "Authentication token required"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Decode token to get user
            try:
                payload = jwt.decode(auth_token, Constants.SECRET_KEY, algorithms=['HS256'])
                user_id = payload[Constants.USER_ID]
            except jwt.ExpiredSignatureError:
                return Response({Constants.JSON_MESSAGE: "Token expired"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({Constants.JSON_MESSAGE: "Invalid token"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            user = UserDetails.objects.filter(userId=user_id).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            room_id = request.data.get('room_id')
            if not room_id:
                return Response({Constants.JSON_MESSAGE: "Room ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            room = PVPRoom.objects.filter(room_id=room_id).first()
            if not room:
                return Response({Constants.JSON_MESSAGE: "Room not found"}, status=status.HTTP_404_NOT_FOUND)
            
            game_result = PVPGameResult.objects.filter(room=room).first()
            if not game_result:
                return Response({Constants.JSON_MESSAGE: "Game result not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Get all players' final scores
            players_data = []
            for player in room.players.all():
                players_data.append({
                    'user_id': player.player.userId,
                    'name': f"{player.player.firstName} {player.player.lastName}",
                    'score': player.score,
                    'correct_answers': player.correct_answers,
                    'total_time': player.total_time,
                    'is_winner': game_result.winner == player.player if game_result.winner else False
                })
            
            # Calculate correct experience for current user
            current_user_experience = 0
            if game_result.winner:
                if game_result.winner == user:
                    current_user_experience = 50  # Winner gets 50 XP
                else:
                    current_user_experience = 10  # Loser gets 10 XP
            else:
                current_user_experience = 20  # Draw gets 20 XP
            
            result_data = {
                'room_id': room.room_id,
                'winner_id': game_result.winner.userId if game_result.winner else None,
                'winner_name': f"{game_result.winner.firstName} {game_result.winner.lastName}" if game_result.winner else None,
                'winner_score': game_result.winner_score,
                'winner_correct_answers': game_result.winner_correct_answers,
                'winner_time': game_result.winner_time,
                'experience_awarded': current_user_experience,
                'is_winner': game_result.winner == user if game_result.winner else False,
                'is_draw': game_result.winner is None,
                'players': players_data,
                'finished_at': room.finished_at
            }
            
            return Response({
                'success': True,
                'data': result_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreatePVPRoom(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            
            user = UserDetails.objects.filter(userId=userId).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Generate unique room code
            import random
            import string
            room_code = ''.join(random.choices(string.digits, k=6))
            
            # Ensure room code is unique
            while PVPRoom.objects.filter(room_id=room_code).exists():
                room_code = ''.join(random.choices(string.digits, k=6))
            
            # Create room
            room = PVPRoom.objects.create(
                room_id=room_code,
                creator=user,
                max_players=request.data.get('max_players', 2),
                number_of_questions=request.data.get('number_of_questions', 10),
                time_per_question=request.data.get('time_per_question', 30),
                difficulty_level=request.data.get('difficulty_level', 'medium'),
                number_of_digits=request.data.get('number_of_digits', 3),
                status='waiting'
            )
            
            # Add creator as first player
            PVPRoomPlayer.objects.create(
                room=room,
                player=user,
                is_ready=True,
                score=0,
                correct_answers=0,
                total_time=0
            )
            
            # Update current players count
            room.current_players = 1
            room.save()
            
            return Response({
                'success': True,
                'data': {
                    'room_id': room.room_id,
                    'creator_id': user.userId,
                    'max_players': room.max_players,
                    'number_of_questions': room.number_of_questions,
                    'time_per_question': room.time_per_question,
                    'status': room.status
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class JoinPVPRoom(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            
            user = UserDetails.objects.filter(userId=userId).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            room_code = request.data.get('room_code')
            if not room_code:
                return Response({Constants.JSON_MESSAGE: "Room code is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            room = PVPRoom.objects.filter(room_id=room_code).first()
            if not room:
                return Response({Constants.JSON_MESSAGE: "Room not found"}, status=status.HTTP_404_NOT_FOUND)
            
            if room.status != 'waiting':
                return Response({Constants.JSON_MESSAGE: "Room is not accepting players"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if user is already in the room
            if PVPRoomPlayer.objects.filter(room=room, player=user).exists():
                return Response({Constants.JSON_MESSAGE: "You are already in this room"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if room is full
            current_players = room.players.count()
            if current_players >= room.max_players:
                return Response({Constants.JSON_MESSAGE: "Room is full"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Add player to room (all players are ready by default)
            PVPRoomPlayer.objects.create(
                room=room,
                player=user,
                is_ready=True,
                score=0,
                correct_answers=0,
                total_time=0
            )
            
            # Update current players count
            room.current_players = room.players.count()
            room.save()
            
            return Response({
                'success': True,
                'data': {
                    'room_id': room.room_id,
                    'message': 'Successfully joined room'
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetPVPRoomDetails(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            
            user = UserDetails.objects.filter(userId=userId).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            room_id = request.data.get('room_id')
            if not room_id:
                return Response({Constants.JSON_MESSAGE: "Room ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            room = PVPRoom.objects.filter(room_id=room_id).first()
            if not room:
                return Response({Constants.JSON_MESSAGE: "Room not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Get all players in the room
            players_data = []
            for player in room.players.all():
                players_data.append({
                    'player': {
                        'userId': player.player.userId,
                        'firstName': player.player.firstName,
                        'lastName': player.player.lastName
                    },
                    'is_ready': player.is_ready,
                    'score': player.score,
                    'correct_answers': player.correct_answers,
                    'total_time': player.total_time
                })
            
            room_data = {
                'room_id': room.room_id,
                'creator': {
                    'userId': room.creator.userId,
                    'firstName': room.creator.firstName,
                    'lastName': room.creator.lastName
                },
                'max_players': room.max_players,
                'current_players': room.players.count(),
                'number_of_questions': room.number_of_questions,
                'time_per_question': room.time_per_question,
                'difficulty_level': room.difficulty_level,
                'status': room.status,
                'players': players_data,
                'created_at': room.created_at
            }
            
            return Response({
                'success': True,
                'data': room_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SetPlayerReady(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            
            user = UserDetails.objects.filter(userId=userId).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            room_id = request.data.get('room_id')
            is_ready = request.data.get('is_ready', False)
            
            if not room_id:
                return Response({Constants.JSON_MESSAGE: "Room ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            room = PVPRoom.objects.filter(room_id=room_id).first()
            if not room:
                return Response({Constants.JSON_MESSAGE: "Room not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Find the player in the room
            player = PVPRoomPlayer.objects.filter(room=room, player=user).first()
            if not player:
                return Response({Constants.JSON_MESSAGE: "You are not in this room"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Update ready status
            player.is_ready = is_ready
            player.save()
            
            return Response({
                'success': True,
                'data': {
                    'message': f"Ready status updated to {is_ready}",
                    'is_ready': is_ready
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StartPVPGame(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            
            user = UserDetails.objects.filter(userId=userId).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            room_id = request.data.get('room_id')
            if not room_id:
                return Response({Constants.JSON_MESSAGE: "Room ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            room = PVPRoom.objects.filter(room_id=room_id).first()
            if not room:
                return Response({Constants.JSON_MESSAGE: "Room not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if user is the creator
            if room.creator != user:
                return Response({Constants.JSON_MESSAGE: "Only the room creator can start the game"}, status=status.HTTP_403_FORBIDDEN)
            
            # Check if room is already active
            if room.status == 'active':
                return Response({Constants.JSON_MESSAGE: "Game is already active"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check player count based on room type
            players = room.players.all()
            if not players.exists():
                return Response({Constants.JSON_MESSAGE: "No players in room"}, status=status.HTTP_400_BAD_REQUEST)
            
            current_player_count = players.count()
            max_players = room.max_players
            
            # Check if we have enough players for the room type
            if current_player_count < max_players:
                return Response({
                    Constants.JSON_MESSAGE: f"Need {max_players} players to start the game. Currently have {current_player_count} players."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # All players are considered ready by default (no ready check needed)
            
            # Update room status to active
            room.status = 'active'
            room.started_at = timezone.now()
            room.save()
            
            # Create game session
            game_session = PVPGameSession.objects.create(
                room=room,
                current_question_index=0,
                is_active=True
            )
            
            # Generate questions for the game
            questions = []
            print(f"Debug: Generating {room.number_of_questions} questions for difficulty: {room.difficulty_level}, digits: {room.number_of_digits}")
            for i in range(room.number_of_questions):
                try:
                    question_data = generatePVPQuestion(room.difficulty_level, room.number_of_digits)
                    print(f"Debug: Question {i+1} data: {question_data}")
                    
                    # Validate question data
                    if not question_data or 'operands' not in question_data or 'correct_answer' not in question_data:
                        print(f"Debug: Invalid question data for question {i+1}, skipping...")
                        continue
                    
                    # Ensure answer is a valid number
                    if not isinstance(question_data['correct_answer'], (int, float)) or question_data['correct_answer'] <= 0:
                        print(f"Debug: Invalid answer for question {i+1}: {question_data['correct_answer']}, skipping...")
                        continue
                    
                    questions.append({
                        'question_id': i + 1,
                        'operands': question_data['operands'],
                        'operator': question_data['operator'],
                        'correct_answer': question_data['correct_answer'],
                        'question_type': question_data['question_type']
                    })
                except Exception as e:
                    print(f"Debug: Error generating question {i+1}: {e}")
                    continue
            
            print(f"Debug: Generated {len(questions)} questions")
            
            # If no questions were generated, create fallback questions
            if len(questions) == 0:
                print("Debug: No questions generated, creating fallback questions...")
                for i in range(room.number_of_questions):
                    questions.append({
                        'question_id': i + 1,
                        'operands': [i + 1, i + 2],
                        'operator': '+',
                        'correct_answer': (i + 1) + (i + 2),
                        'question_type': 'basic'
                    })
            
            # Store questions in game session (you might want to create a separate model for this)
            game_session.questions_data = questions
            game_session.save()
            
            return Response({
                'success': True,
                'data': {
                    'message': 'Game started successfully',
                    'game_session_id': game_session.id,
                    'room_status': room.status,
                    'questions': questions,
                    'total_questions': room.number_of_questions,
                    'time_per_question': room.time_per_question
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubmitPVPGameResult(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            requestUserToken = request.headers[Constants.TOKEN_HEADER]
            try:
                userId = IdExtraction(requestUserToken)
                if isinstance(userId, Exception):
                    raise Exception(Constants.INVALID_TOKEN_MESSAGE)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_403_FORBIDDEN)
            
            user = UserDetails.objects.filter(userId=userId).first()
            if user is None:
                return Response({Constants.JSON_MESSAGE: "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            room_id = request.data.get('room_id')
            score = request.data.get('score', 0)
            correct_answers = request.data.get('correct_answers', 0)
            total_time = request.data.get('total_time', 0)
            
            if not room_id:
                return Response({Constants.JSON_MESSAGE: "Room ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            room = PVPRoom.objects.filter(room_id=room_id).first()
            if not room:
                return Response({Constants.JSON_MESSAGE: "Room not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Find the player in the room
            player = PVPRoomPlayer.objects.filter(room=room, player=user).first()
            if not player:
                return Response({Constants.JSON_MESSAGE: "You are not in this room"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Update player's game results
            player.score = score
            player.correct_answers = correct_answers
            player.total_time = total_time
            player.status = 'finished'  # Mark player as finished
            player.finished_at = timezone.now()
            player.save()
            
            # Check if all players have finished
            all_players = room.players.all()
            finished_players = all_players.filter(status='finished')  # Players who have finished the game
            
            print(f"Debug: Room {room_id} - Total players: {all_players.count()}, Finished players: {finished_players.count()}")
            for p in all_players:
                print(f"Debug: Player {p.player.firstName} - Status: {p.status}, Score: {p.score}")
            
            if finished_players.count() == all_players.count():
                # All players finished, determine winner
                # Check if it's a draw (all players have same score)
                scores = [p.score for p in finished_players]
                print(f"Debug: All scores: {scores}")
                print(f"Debug: Unique scores: {set(scores)}")
                print(f"Debug: Number of unique scores: {len(set(scores))}")
                is_draw = len(set(scores)) == 1 and len(scores) > 1
                print(f"Debug: Is draw: {is_draw}")
                
                if is_draw:
                    # It's a draw - all players get 20 XP
                    winner = None
                    experience_awarded = 20
                    
                    # Award 20 XP to all players in draw
                    for player in all_players:
                        user_exp, created = UserExperience.objects.get_or_create(
                            user=player.player,
                            defaults={'experience_points': 0, 'level': 1}
                        )
                        old_xp = user_exp.experience_points
                        user_exp.experience_points += 20
                        # Level calculation: 0-90 = Level 1, 100+ = Level 2+
                        if user_exp.experience_points <= 90:
                            user_exp.level = 1
                        else:
                            user_exp.level = ((user_exp.experience_points - 90) // 100) + 2
                        user_exp.save()
                        print(f"Debug: Draw player {player.player.firstName} - XP: {old_xp} -> {user_exp.experience_points}")
                    
                    # Create game result for draw
                    game_result = PVPGameResult.objects.create(
                        room=room,
                        winner=None,  # No winner in draw
                        winner_score=scores[0],  # All have same score
                        winner_correct_answers=finished_players.first().correct_answers,
                        winner_time=finished_players.first().total_time,
                        experience_awarded=20
                    )
                    
                    result_data = {
                        'is_winner': None,  # No winner in draw
                        'is_draw': True,
                        'winner_name': None,
                        'winner_score': scores[0],
                        'experience_awarded': 20,
                        'total_players': all_players.count()
                    }
                else:
                    # Normal game - determine winner
                    winner = finished_players.order_by('-score', 'total_time').first()
                    
                    # Create game result
                    game_result = PVPGameResult.objects.create(
                        room=room,
                        winner=winner.player if winner else None,
                        winner_score=winner.score if winner else 0,
                        winner_correct_answers=winner.correct_answers if winner else 0,
                        winner_time=winner.total_time if winner else 0,
                        experience_awarded=50 if winner else 20  # Winner gets 50 XP, draw gives 20 each (handled above), losers 10
                    )
                    
                    # Award experience to winner
                    if winner:
                        user_exp, created = UserExperience.objects.get_or_create(
                            user=winner.player,
                            defaults={'experience_points': 0, 'level': 1}
                        )
                        old_xp = user_exp.experience_points
                        user_exp.experience_points += 50
                        # Level calculation: 0-90 = Level 1, 100+ = Level 2+
                        if user_exp.experience_points <= 90:
                            user_exp.level = 1
                        else:
                            user_exp.level = ((user_exp.experience_points - 90) // 100) + 2
                        user_exp.save()
                        print(f"Debug: Winner {winner.player.firstName} - XP: {old_xp} -> {user_exp.experience_points}")
                    
                    # Award experience to all participants (losers)
                    for player in all_players:
                        if winner and player.player != winner.player:
                            user_exp, created = UserExperience.objects.get_or_create(
                                user=player.player,
                                defaults={'experience_points': 0, 'level': 1}
                            )
                            old_xp = user_exp.experience_points
                            user_exp.experience_points += 10
                            # Level calculation: 0-90 = Level 1, 100+ = Level 2+
                            if user_exp.experience_points <= 90:
                                user_exp.level = 1
                            else:
                                user_exp.level = ((user_exp.experience_points - 90) // 100) + 2
                            user_exp.save()
                            print(f"Debug: Loser {player.player.firstName} - XP: {old_xp} -> {user_exp.experience_points}")
                    
                    # Determine if current user is the winner
                    current_user_is_winner = winner and winner.player == user
                    
                    print(f"Debug: Winner player: {winner.player.firstName if winner else 'None'}")
                    print(f"Debug: Current user: {user.firstName}")
                    print(f"Debug: Current user is winner: {current_user_is_winner}")
                    print(f"Debug: Winner score: {winner.score if winner else 'None'}")
                    print(f"Debug: Current user score: {score}")
                    
                    result_data = {
                        'is_winner': current_user_is_winner,
                        'is_draw': False,
                        'winner_name': f"{winner.player.firstName} {winner.player.lastName}" if winner else None,
                        'winner_score': winner.score if winner else 0,
                        'experience_awarded': 50 if current_user_is_winner else 10,
                        'total_players': all_players.count()
                    }
                    
                    print(f"Debug: Final result_data: {result_data}")
                
                # Update room status to finished (for both draw and normal game)
                room.status = 'finished'
                room.finished_at = timezone.now()
                room.save()
            else:
                # Not all players finished yet
                result_data = {
                    'is_winner': None,
                    'winner_name': None,
                    'winner_score': 0,
                    'experience_awarded': 0,
                    'total_players': all_players.count(),
                    'finished_players': finished_players.count()
                }
            
            return Response({
                'success': True,
                'data': result_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: repr(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Create your views here.

class UpdatePlayerProgress(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """Update player progress during PVP game for real-time leaderboard"""
        print(f"🔵 UpdatePlayerProgress called with data: {request.data}")
        print(f"🔵 Headers: {request.headers}")
        
        try:
            # Extract token from headers
            auth_token = request.headers.get('auth-token')
            print(f"🔵 Auth token: {auth_token[:20] if auth_token else 'None'}...")
            
            if not auth_token:
                print("❌ No auth token found")
                return Response({
                    'success': False,
                    'message': 'Authentication token required'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Decode token to get user
            try:
                payload = jwt.decode(auth_token, Constants.SECRET_KEY, algorithms=['HS256'])
                user_id = payload[Constants.USER_ID]
                print(f"🔵 Decoded user_id: {user_id}")
            except jwt.ExpiredSignatureError:
                print("❌ Token expired")
                return Response({
                    'success': False,
                    'message': 'Token expired'
                }, status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError as e:
                print(f"❌ Invalid token: {e}")
                return Response({
                    'success': False,
                    'message': 'Invalid token'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get user
            try:
                user = UserDetails.objects.get(userId=user_id)
                print(f"🔵 Found user: {user.firstName}")
            except UserDetails.DoesNotExist:
                print(f"❌ User not found with ID: {user_id}")
                return Response({
                    'success': False,
                    'message': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get request data
            room_id = request.data.get('room_id')
            score = request.data.get('score', 0)
            correct_answers = request.data.get('correct_answers', 0)
            current_question = request.data.get('current_question', 1)
            
            print(f"🔵 Request data - Room: {room_id}, Score: {score}, Correct: {correct_answers}, Question: {current_question}")
            
            if not room_id:
                print("❌ No room_id provided")
                return Response({
                    'success': False,
                    'message': 'Room ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get room
            try:
                room = PVPRoom.objects.get(room_id=room_id)
                print(f"🔵 Found room: {room.room_id}")
            except PVPRoom.DoesNotExist:
                print(f"❌ Room not found: {room_id}")
                return Response({
                    'success': False,
                    'message': 'Room not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get or create player session
            player_session, created = PVPRoomPlayer.objects.get_or_create(
                room=room,
                player=user,
                defaults={
                    'score': score,
                    'correct_answers': correct_answers,
                    'total_time': 0,
                    'status': 'playing'
                }
            )
            
            if not created:
                # Update existing session
                print(f"🔵 Updating existing player session - Old score: {player_session.score}, New score: {score}")
                player_session.score = score
                player_session.correct_answers = correct_answers
                player_session.save()
            else:
                print(f"🔵 Created new player session with score: {score}")
            
            print(f"✅ Player {user.firstName} progress updated - Score: {score}, Correct: {correct_answers}")
            
            return Response({
                'success': True,
                'message': 'Player progress updated successfully',
                'data': {
                    'score': score,
                    'correct_answers': correct_answers,
                    'current_question': current_question
                }
            })
            
        except Exception as e:
            print(f"❌ Error updating player progress: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'message': f'Error updating player progress: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetPVPLeaderboard(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # Get top 10 players by experience points (only those with XP > 0)
            top_players = UserExperience.objects.select_related('user').filter(experience_points__gt=0).order_by('-experience_points')[:10]
            
            print(f"Debug: Found {top_players.count()} players with experience > 0")
            for player in top_players:
                print(f"Debug: Player {player.user.firstName} - XP: {player.experience_points}")
            
            leaderboard_data = []
            for rank, player in enumerate(top_players, 1):
                # Calculate current level based on experience points
                if player.experience_points <= 90:
                    current_level = 1
                else:
                    current_level = ((player.experience_points - 90) // 100) + 2
                
                leaderboard_data.append({
                    'rank': rank,
                    'user_id': player.user.userId,
                    'name': f"{player.user.firstName} {player.user.lastName}",
                    'experience_points': player.experience_points,
                    'level': current_level
                })
            
            return Response({
                'success': True,
                'data': {
                    'leaderboard': leaderboard_data,
                    'total_players': UserExperience.objects.count()
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error fetching leaderboard: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Streak Management APIs
class GetUserStreak(APIView):
    """Get user's current streak information"""
    authentication_classes = []  # Disable DRF authentication
    permission_classes = [AllowAny]
    
    def get(self, request):
        return self._handle_request(request)
    
    def post(self, request):
        return self._handle_request(request)
    
    def _handle_request(self, request):
        try:
            # Debug logging
            print(f"[DEBUG] Streak request headers: {dict(request.headers)}")
            print(f"[DEBUG] Looking for header: {Constants.TOKEN_HEADER}")
            
            # Extract token from headers
            auth_token = request.headers.get(Constants.TOKEN_HEADER)
            print(f"[DEBUG] Auth token found: {auth_token is not None}")
            
            if not auth_token:
                print("[DEBUG] No auth token found, returning 401")
                return Response({Constants.JSON_MESSAGE: "Authentication token required"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Decode token to get user
            try:
                payload = jwt.decode(auth_token, Constants.SECRET_KEY, algorithms=['HS256'])
                user_id = payload[Constants.USER_ID]
            except jwt.ExpiredSignatureError:
                return Response({Constants.JSON_MESSAGE: "Token expired"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({Constants.JSON_MESSAGE: "Invalid token"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Get user
            try:
                user = UserDetails.objects.get(userId=user_id)
            except UserDetails.DoesNotExist:
                return Response({Constants.JSON_MESSAGE: "User not found"}, 
                              status=status.HTTP_404_NOT_FOUND)
            
            # Get or create user streak using the enhanced method
            try:
                user_streak, created = UserStreak.get_or_create_streak(user)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: f"Error accessing streak data: {str(e)}"}, 
                              status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                'currentStreak': user_streak.current_streak,
                'maxStreak': user_streak.max_streak,
                'lastActivityDate': user_streak.last_activity_date.isoformat() if user_streak.last_activity_date else None,
                'createdAt': user_streak.created_at.isoformat(),
                'updatedAt': user_streak.updated_at.isoformat(),
                'streakCreated': created
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: f"Error fetching streak: {str(e)}"}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetUserStreakById(APIView):
    """Get any user's streak by userId (admin/public for leaderboard usage)."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data or {}
            target_user_id = data.get('userId')
            if not target_user_id:
                return Response({Constants.JSON_MESSAGE: 'userId is required'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                user = UserDetails.objects.get(userId=target_user_id)
            except UserDetails.DoesNotExist:
                return Response({Constants.JSON_MESSAGE: 'User not found'}, status=status.HTTP_404_NOT_FOUND)

            try:
                user_streak, created = UserStreak.get_or_create_streak(user)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: f"Error accessing streak data: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({
                'currentStreak': user_streak.current_streak,
                'maxStreak': user_streak.max_streak,
                'lastActivityDate': user_streak.last_activity_date.isoformat() if user_streak.last_activity_date else None,
                'createdAt': user_streak.created_at.isoformat(),
                'updatedAt': user_streak.updated_at.isoformat(),
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: f"Error fetching streak by id: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UpdateUserStreak(APIView):
    """Update user's streak (increment for daily activity)"""
    authentication_classes = []  # Disable DRF authentication
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            # Extract token from headers
            auth_token = request.headers.get(Constants.TOKEN_HEADER)
            
            if not auth_token:
                return Response({Constants.JSON_MESSAGE: "Authentication token required"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Decode token to get user
            try:
                payload = jwt.decode(auth_token, Constants.SECRET_KEY, algorithms=['HS256'])
                user_id = payload[Constants.USER_ID]
            except jwt.ExpiredSignatureError:
                return Response({Constants.JSON_MESSAGE: "Token expired"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({Constants.JSON_MESSAGE: "Invalid token"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Get user
            try:
                user = UserDetails.objects.get(userId=user_id)
            except UserDetails.DoesNotExist:
                return Response({Constants.JSON_MESSAGE: "User not found"}, 
                              status=status.HTTP_404_NOT_FOUND)
            
            # Get or create user streak using the enhanced method
            try:
                user_streak, created = UserStreak.get_or_create_streak(user)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: f"Error accessing streak data: {str(e)}"}, 
                              status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Update streak with proper error handling
            try:
                new_streak = user_streak.update_streak()
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: f"Error updating streak: {str(e)}"}, 
                              status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                'currentStreak': user_streak.current_streak,
                'maxStreak': user_streak.max_streak,
                'lastActivityDate': user_streak.last_activity_date.isoformat() if user_streak.last_activity_date else None,
                'streakUpdated': True,
                'newStreak': new_streak,
                'streakCreated': created
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: f"Error updating streak: {str(e)}"}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResetUserStreak(APIView):
    """Reset user's streak to 0"""
    authentication_classes = []  # Disable DRF authentication
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            # Extract token from headers
            auth_token = request.headers.get(Constants.TOKEN_HEADER)
            
            if not auth_token:
                return Response({Constants.JSON_MESSAGE: "Authentication token required"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Decode token to get user
            try:
                payload = jwt.decode(auth_token, Constants.SECRET_KEY, algorithms=['HS256'])
                user_id = payload[Constants.USER_ID]
            except jwt.ExpiredSignatureError:
                return Response({Constants.JSON_MESSAGE: "Token expired"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({Constants.JSON_MESSAGE: "Invalid token"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Get user
            try:
                user = UserDetails.objects.get(userId=user_id)
            except UserDetails.DoesNotExist:
                return Response({Constants.JSON_MESSAGE: "User not found"}, 
                              status=status.HTTP_404_NOT_FOUND)
            
            # Get or create user streak using the enhanced method
            try:
                user_streak, created = UserStreak.get_or_create_streak(user)
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: f"Error accessing streak data: {str(e)}"}, 
                              status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Reset streak using the enhanced method
            try:
                user_streak.reset_streak()
            except Exception as e:
                return Response({Constants.JSON_MESSAGE: f"Error resetting streak: {str(e)}"}, 
                              status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                'currentStreak': user_streak.current_streak,
                'maxStreak': user_streak.max_streak,
                'lastActivityDate': user_streak.last_activity_date.isoformat() if user_streak.last_activity_date else None,
                'streakReset': True,
                'streakCreated': created
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: f"Error resetting streak: {str(e)}"}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetAccuracyTrend(APIView):
    authentication_classes = []  # Disable DRF authentication
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # Debug logging
            print(f"[DEBUG] Accuracy trend request headers: {dict(request.headers)}")
            
            # Extract token from headers
            auth_token = request.headers.get(Constants.TOKEN_HEADER)
            print(f"[DEBUG] Auth token found: {auth_token is not None}")
            
            if not auth_token:
                print("[DEBUG] No auth token found, returning 401")
                return Response({Constants.JSON_MESSAGE: "Authentication token required"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Decode token to get user
            try:
                payload = jwt.decode(auth_token, Constants.SECRET_KEY, algorithms=['HS256'])
                user_id = payload[Constants.USER_ID]
            except jwt.ExpiredSignatureError:
                return Response({Constants.JSON_MESSAGE: "Token expired"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({Constants.JSON_MESSAGE: "Invalid token"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Get user's progress data for the last 7 days
            from datetime import datetime, timedelta
            seven_days_ago = datetime.now() - timedelta(days=7)
            
            # Get progress records from the last 7 days
            recent_progress = Progress.objects.filter(
                user_id=user_id,
                created_at__gte=seven_days_ago
            ).order_by('created_at')
            
            # Calculate daily accuracy
            daily_accuracy = []
            current_date = seven_days_ago.date()
            today = datetime.now().date()
            
            while current_date <= today:
                day_progress = recent_progress.filter(created_at__date=current_date)
                
                if day_progress.exists():
                    # Use percentage field from Progress model
                    total_percentage = sum(p.percentage for p in day_progress)
                    count = day_progress.count()
                    accuracy = total_percentage / count if count > 0 else 0
                else:
                    accuracy = 0
                
                daily_accuracy.append(round(accuracy, 1))
                current_date += timedelta(days=1)
            
            # Calculate current accuracy (last non-zero day)
            current_accuracy = 0
            for acc in reversed(daily_accuracy):
                if acc > 0:
                    current_accuracy = acc
                    break
            
            # Calculate weekly progress
            weekly_progress = 0
            if len(daily_accuracy) >= 2:
                first_day = daily_accuracy[0]
                last_day = daily_accuracy[-1]
                weekly_progress = round(last_day - first_day, 1)
            
            return Response({
                'currentAccuracy': current_accuracy,
                'weeklyProgress': weekly_progress,
                'dailyAccuracy': daily_accuracy,
                'labels': [f"{i}d ago" if i > 0 else "Today" for i in range(len(daily_accuracy))]
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: f"Error getting accuracy trend: {str(e)}"}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetSpeedTrend(APIView):
    authentication_classes = []  # Disable DRF authentication
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # Extract token from headers
            auth_token = request.headers.get(Constants.TOKEN_HEADER)
            
            if not auth_token:
                return Response({Constants.JSON_MESSAGE: "Authentication token required"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Decode token to get user
            try:
                payload = jwt.decode(auth_token, Constants.SECRET_KEY, algorithms=['HS256'])
                user_id = payload[Constants.USER_ID]
            except jwt.ExpiredSignatureError:
                return Response({Constants.JSON_MESSAGE: "Token expired"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({Constants.JSON_MESSAGE: "Invalid token"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Get user's progress data for the last 7 days
            from datetime import datetime, timedelta
            seven_days_ago = datetime.now() - timedelta(days=7)
            
            # Get progress records from the last 7 days
            recent_progress = Progress.objects.filter(
                user_id=user_id,
                created_at__gte=seven_days_ago
            ).order_by('created_at')
            
            # Calculate daily speed (problems per minute)
            daily_speed = []
            current_date = seven_days_ago.date()
            today = datetime.now().date()
            
            while current_date <= today:
                day_progress = recent_progress.filter(created_at__date=current_date)
                
                if day_progress.exists():
                    # Use score as number of problems solved and time field from Progress model
                    total_problems = sum(p.score for p in day_progress)  # score represents problems solved
                    total_time_minutes = sum(p.time for p in day_progress) / 60  # time is in seconds
                    
                    if total_time_minutes > 0:
                        speed = total_problems / total_time_minutes
                    else:
                        speed = 0
                else:
                    speed = 0
                
                daily_speed.append(round(speed, 1))
                current_date += timedelta(days=1)
            
            # Calculate current speed (last non-zero day)
            current_speed = 0
            for speed in reversed(daily_speed):
                if speed > 0:
                    current_speed = speed
                    break
            
            # Calculate weekly progress
            weekly_progress = 0
            if len(daily_speed) >= 2:
                first_day = daily_speed[0]
                last_day = daily_speed[-1]
                weekly_progress = round(last_day - first_day, 1)
            
            return Response({
                'currentSpeed': current_speed,
                'weeklyProgress': weekly_progress,
                'dailySpeed': daily_speed,
                'labels': [f"{i}d ago" if i > 0 else "Today" for i in range(len(daily_speed))]
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({Constants.JSON_MESSAGE: f"Error getting speed trend: {str(e)}"}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)