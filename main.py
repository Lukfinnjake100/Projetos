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
    # Alternativa escolhida (1 a 4), pode ser None para abstenção
    user_answer: Optional[int]
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

    # Verificar se o nome de usuário já existe
    existing_users = r.keys("user:*")
    for existing_user_key in existing_users:
        existing_user_data = r.hgetall(existing_user_key)
        if existing_user_data.get("name") == user.name:
            raise HTTPException(
                status_code=400, detail="Username already exists")

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

    # Registrar a resposta do usuário
    if answer.user_answer is not None:
        r.hincrby(
            f"question_votes:{answer.question_id}", answer.user_answer, 1)
    else:
        r.hincrby(f"question_votes:{answer.question_id}", "abstention", 1)

    # Obter votos da questão
    votes = r.hgetall(f"question_votes:{answer.question_id}")
    max_votes = max(votes.values())
    most_voted_alt = [alt for alt,
                      count in votes.items() if count == max_votes][0]

    # Atualizar contagem de acertos e erros
    if is_correct:
        r.hincrby(f"question_stats:{answer.question_id}", "correct", 1)
    elif answer.user_answer is not None:
        r.hincrby(f"question_stats:{answer.question_id}", "incorrect", 1)
    else:
        r.hincrby(f"question_stats:{answer.question_id}", "abstention", 1)

    # Atualizar resposta mais rápida
    fastest_user_key = f"fastest_user:{answer.question_id}"
    fastest_time = r.hget(fastest_user_key, "time")
    if fastest_time is None or response_time < float(fastest_time):
        r.hset(fastest_user_key, mapping={
               "user_id": answer.user_id, "time": response_time})

    fastest_user_data = r.hgetall(fastest_user_key)
    fastest_user_name = r.hget(
        f"user:{fastest_user_data.get('user_id')}", "name")

    most_voted_text = question_data.get(f"alt{most_voted_alt}", "Abstention")

    return {
        "question_id": answer.question_id,
        "user_answer": answer.user_answer,
        "correct_answer": correct_alt,
        "is_correct": is_correct,
        "response_time_seconds": response_time,
        "finished_at": finished_at.isoformat(),
        "votes": votes,
        "most_voted_alt": most_voted_alt,
        "most_voted_text": most_voted_text,
        "fastest_user_name": fastest_user_name,
        "fastest_user_response_time": fastest_user_data.get("time")
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


@app.get("/question_votes/{question_id}")
def get_question_votes(question_id: int):
    votes = r.hgetall(f"question_votes:{question_id}")
    if not votes:
        raise HTTPException(
            status_code=404, detail="No votes found for this question")

    max_votes = max(votes.values())
    most_voted_alt = [alt for alt,
                      count in votes.items() if count == max_votes][0]
    question_key = f"question:{question_id}"
    question_data = r.hgetall(question_key)
    most_voted_text = question_data.get(f"alt{most_voted_alt}")

    return {
        "question_id": question_id,
        "most_voted_alt": most_voted_alt,
        "most_voted_text": most_voted_text,
        "votes": votes
    }


@app.get("/question_stats")
def get_question_stats():
    question_keys = r.keys("question_stats:*")
    correct_stats = []
    incorrect_stats = []

    for key in question_keys:
        question_id = int(key.split(":")[1])
        stats = r.hgetall(key)
        question_data = r.hgetall(f"question:{question_id}")
        question_text = question_data.get("question_text", "").rstrip("?")
        correct_stats.append({
            "question_id": question_id,
            "question_text": question_text,
            "correct": int(stats.get("correct", 0))
        })
        incorrect_stats.append({
            "question_id": question_id,
            "question_text": question_text,
            "incorrect": int(stats.get("incorrect", 0))
        })

    correct_stats.sort(key=lambda x: x["correct"], reverse=True)
    incorrect_stats.sort(key=lambda x: x["incorrect"], reverse=True)

    return {
        "top_correct": correct_stats[:5],
        "top_incorrect": incorrect_stats[:5]
    }


@app.get("/user_stats")
def get_user_stats(user_id: int):
    correct = 0
    incorrect = 0
    abstention = 0

    answered_questions = r.smembers(f"answered:{user_id}")
    for question_id in answered_questions:
        stats = r.hgetall(f"question_stats:{question_id}")
        correct += int(stats.get("correct", 0))
        incorrect += int(stats.get("incorrect", 0))
        abstention += int(stats.get("abstention", 0))

    return {
        "correct": correct,
        "incorrect": incorrect,
        "abstention": abstention
    }


@app.get("/fastest_users")
def get_fastest_users():
    fastest_users = []
    question_keys = r.keys("fastest_user:*")

    for key in question_keys:
        fastest_user_data = r.hgetall(key)
        user_id = fastest_user_data.get("user_id")
        time = float(fastest_user_data.get("time"))
        user_name = r.hget(f"user:{user_id}", "name")
        fastest_users.append({"name": user_name, "time": time})

    fastest_users.sort(key=lambda x: x["time"])
    return fastest_users[:5]


if __name__ == '__main__':
    app.run(debug=True)
