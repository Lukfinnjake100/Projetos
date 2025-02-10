from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
from typing import List, Optional
from datetime import datetime
import random

app = FastAPI()
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# Substitua por domínios específicos em produção
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],)


class Question(BaseModel):
    question_id: int
    question_text: str
    alt1: str
    alt2: str
    alt3: str
    alt4: str
    correct_alt: int  # Número da alternativa correta (1 a 4)


class Answer(BaseModel):
    question_id: int
    user_id: int  # Adicionado user_id
    user_answer: int  # Alternativa escolhida (1 a 4)
    started_at: str
    finished_at: str  # Adicionado finished_at


class User(BaseModel):
    user_id: int
    name: str
    password: str
    points: int = 1000  # Iniciar com 1000 pontos
    ranking: int = 0


class LoginData(BaseModel):
    name: str
    password: str


@app.post("/register")
def register_user(user: User):
    user_key = f"user:{user.user_id}"

    if r.exists(user_key):
        raise HTTPException(status_code=400, detail="User already exists")

    r.hset(user_key, mapping={
        "user_id": user.user_id,
        "name": user.name,
        "password": user.password,
        "points": user.points,
        "ranking": user.ranking
    })

    return {"message": "User registered successfully"}


@app.post("/login")
def login_user(login_data: LoginData):
    user_keys = r.keys("user:*")
    for user_key in user_keys:
        user_data = r.hgetall(user_key)
        if user_data.get("name") == login_data.name and user_data.get("password") == login_data.password:
            return {"user_id": user_data.get("user_id"), "name": user_data.get("name"), "message": "Login successful"}

    raise HTTPException(status_code=400, detail="Invalid username or password")


@app.get("/question/{question_id}")
def get_question(question_id: int):
    question_key = f"question:{question_id}"
    question_data = r.hgetall(question_key)
    if not question_data:
        raise HTTPException(status_code=404, detail="Question not found")
    return {
        "question_id": question_id,
        "question_text": question_data.get("question_text"),
        "alternatives": {
            1: question_data.get("alt1"),
            2: question_data.get("alt2"),
            3: question_data.get("alt3"),
            4: question_data.get("alt4"),
        }
    }


@app.get("/questions")
def get_all_questions():
    keys = r.keys("question:*")
    questions = []

    for key in keys:
        question_data = r.hgetall(key)
        question_id = int(key.split(":")[1])
        questions.append({
            "question_id": question_id,
            "question_text": question_data.get("question_text"),
            "alternatives": {
                1: question_data.get("alt1"),
                2: question_data.get("alt2"),
                3: question_data.get("alt3"),
                4: question_data.get("alt4"),
            }
        })

    return {"questions": questions}


@app.post("/questions")
def create_questions(questions: List[Question]):
    created = []
    skipped = []

    for question in questions:
        question_key = f"question:{question.question_id}"

        if r.exists(question_key):
            skipped.append({"question_id": question.question_id,
                           "message": "Question already exists"})
            continue

        r.hset(question_key, mapping={
            "question_text": question.question_text,
            "alt1": question.alt1,
            "alt2": question.alt2,
            "alt3": question.alt3,
            "alt4": question.alt4,
            "correct_alt": question.correct_alt
        })
        created.append({"question_id": question.question_id,
                       "message": "Question has been created"})

    return {"created": created, "skipped": skipped}


@app.post("/answer")
def answer_question(answer: Answer):
    question_key = f"question:{answer.question_id}"
    question_data = r.hgetall(question_key)
    if not question_data:
        raise HTTPException(status_code=404, detail="Question not found")

    try:
        started_at = datetime.fromisoformat(answer.started_at)
        finished_at = datetime.fromisoformat(answer.finished_at)
        if finished_at < started_at:
            raise ValueError("finished_at cannot be before started_at")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    response_time = (finished_at - started_at).total_seconds()
    correct_alt = int(question_data.get("correct_alt"))
    is_correct = answer.user_answer == correct_alt

    if response_time > 20:
        is_correct = False

    if is_correct:
        user_key = f"user:{answer.user_id}"
        if r.exists(user_key):
            points_to_add = max(100 - response_time, 0)
            r.hincrbyfloat(user_key, "points", points_to_add)
            r.zadd("ranking", {user_key: float(r.hget(user_key, "points"))})
        else:
            raise HTTPException(status_code=404, detail="User not found")

    # Marcar a questão como respondida pelo usuário
    r.sadd(f"answered:{answer.user_id}", answer.question_id)

    return {
        "question_id": answer.question_id,
        "user_answer": answer.user_answer,
        "correct_answer": correct_alt,
        "is_correct": is_correct,
        "response_time_seconds": response_time,
        "finished_at": finished_at.isoformat()
    }


@app.get("/leaderboard")
def get_leaderboard():
    user_keys = r.zrevrange("ranking", 0, 4, withscores=True)
    users = []

    for user_key, points in user_keys:
        user_data = r.hgetall(user_key)
        if user_data:
            user_id = user_data.get("user_id")
            if user_id is not None:
                users.append({
                    "user_id": int(user_id),
                    "name": user_data.get("name"),
                    "points": points,
                    "ranking": int(user_data.get("ranking", 0))
                })

    for i, user in enumerate(users):
        user["ranking"] = i + 1
        user_key = f"user:{user['user_id']}"
        r.hset(user_key, "ranking", user["ranking"])

    return {"leaderboard": users}


@app.get("/random_question")
def get_random_question(user_id: int):
    answered_questions = r.smembers(f"answered:{user_id}")
    keys = [key for key in r.keys(
        "question:*") if key.split(":")[1] not in answered_questions]
    if not keys:
        raise HTTPException(
            status_code=404, detail="No new questions available")
    random_key = random.choice(keys)
    question_data = r.hgetall(random_key)
    question_id = int(random_key.split(":")[1])
    return {
        "question_id": question_id,
        "question_text": question_data.get("question_text"),
        "alternatives": {
            1: question_data.get("alt1"),
            2: question_data.get("alt2"),
            3: question_data.get("alt3"),
            4: question_data.get("alt4"),
        }
    }


if __name__ == '__main__':
    app.run(debug=True)
