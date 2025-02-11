let timerInterval;
let startTime;
let user_id;
let user_name;
let currentQuestionId;
let timerChart;
let timerChartConfig;

async function registerUser() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    const response = await fetch('http://127.0.0.1:8000/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ user_id: Date.now(), name: username, password: password })
    });

    const responseData = await response.json();
    document.getElementById('response').textContent = JSON.stringify(responseData, null, 2);
    if (responseData.message === "User registered successfully") {
        loginUser();
    }
}

async function loginUser() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    const response = await fetch('http://127.0.0.1:8000/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: username, password: password })
    });

    const responseData = await response.json();
    if (responseData.user_id) {
        user_id = responseData.user_id;
        user_name = responseData.name;
        document.getElementById('authContainer').style.display = 'none';
        getQuestion();
        showLeaderboard();
        showQuestionStats();
        showFastestUsers();
        updateScores();
    } else {
        document.getElementById('response').textContent = JSON.stringify(responseData, null, 2);
    }
}

async function getQuestion() {
    const response = await fetch(`http://127.0.0.1:8000/random_question?user_id=${user_id}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    });
    const question = await response.json();
    currentQuestionId = question.question_id;
    displayQuestion(question);
}

function displayQuestion(question) {
    document.getElementById('questionText').textContent = question.question_text;
    const alternativesDiv = document.getElementById('alternatives');
    alternativesDiv.innerHTML = '';
    for (const [key, value] of Object.entries(question.alternatives)) {
        const button = document.createElement('button');
        button.textContent = value;
        button.className = 'answer-button';
        button.onclick = () => submitAnswer(question.question_id, parseInt(key));
        alternativesDiv.appendChild(button);
    }
    document.getElementById('questionContainer').style.display = 'block';
    startTimer();
}

function startTimer() {
    clearInterval(timerInterval);
    let timeLeft = 20;
    document.getElementById('timer').textContent = timeLeft;
    startTime = new Date().toISOString();
    timerInterval = setInterval(() => {
        timeLeft--;
        document.getElementById('timer').textContent = timeLeft;
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            submitAnswerAbstention();
        }
    }, 1000);
}

async function submitAnswer(question_id, user_answer) {
    clearInterval(timerInterval);
    const started_at = startTime;
    const finished_at = new Date().toISOString();
    
    const response = await fetch('http://127.0.0.1:8000/answer', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            user_id: user_id,
            question_id: question_id,
            user_answer: user_answer,
            started_at: started_at,
            finished_at: finished_at
        })
    });
    
    const responseData = await response.json();
    document.getElementById('response').textContent = JSON.stringify(responseData, null, 2);
    await showLeaderboard();
    showNextQuestionTimer();
    updateScores();

    // Exibir votos
    const votes = responseData.votes;
    const mostVotedText = responseData.most_voted_text;
    document.getElementById('response').textContent += `\nA alternativa mais votada foi: "${mostVotedText}" com ${votes[responseData.most_voted_alt]} votos.\n`;
    for (const [alt, count] of Object.entries(votes)) {
        document.getElementById('response').textContent += `Alternativa ${alt}: ${count} votos\n`;
    }

    // Exibir o usuário mais rápido
    const fastestUserName = responseData.fastest_user_name;
    const fastestUserResponseTime = responseData.fastest_user_response_time;
    document.getElementById('response').textContent += `\nO usuário mais rápido foi: ${fastestUserName} com um tempo de resposta de ${fastestUserResponseTime} segundos.\n`;
}

async function submitAnswerAbstention() {
    const started_at = startTime;
    const finished_at = new Date().toISOString();
    
    const response = await fetch('http://127.0.0.1:8000/answer', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            user_id: user_id,
            question_id: currentQuestionId,
            user_answer: null,
            started_at: started_at,
            finished_at: finished_at
        })
    });
    
    const responseData = await response.json();
    document.getElementById('response').textContent = JSON.stringify(responseData, null, 2);
    await showLeaderboard();
    showNextQuestionTimer();
    updateScores();

    // Exibir votos
    const votes = responseData.votes;
    const mostVotedText = responseData.most_voted_text;
    document.getElementById('response').textContent += `\nA alternativa mais votada foi: "${mostVotedText}" com ${votes[responseData.most_voted_alt]} votos.\n`;
    for (const [alt, count] of Object.entries(votes)) {
        document.getElementById('response').textContent += `Alternativa ${alt}: ${count} votos\n`;
    }

    // Exibir o usuário mais rápido
    const fastestUserName = responseData.fastest_user_name;
    const fastestUserResponseTime = responseData.fastest_user_response_time;
    document.getElementById('response').textContent += `\nO usuário mais rápido foi: ${fastestUserName} com um tempo de resposta de ${fastestUserResponseTime} segundos.\n`;
}

async function showLeaderboard() {
    const response = await fetch('http://127.0.0.1:8000/leaderboard', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    });
    const leaderboard = await response.json();
    const user = leaderboard.leaderboard.find(u => u.user_id == user_id);
    let leaderboardText = '';
    if (user) {
        leaderboardText += `Your position: ${user.ranking}, Name: ${user_name}, Points: ${user.points}\n`;
    }
    leaderboardText += `Top 5 Leaderboard:\n`;
    leaderboard.leaderboard.forEach((u, index) => {
        leaderboardText += `${index + 1}. ${u.name} - ${u.points} points\n`;
    });
    document.getElementById('leaderboard').textContent = leaderboardText;
}

async function showQuestionStats() {
    const response = await fetch('http://127.0.0.1:8000/question_stats', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    });
    const stats = await response.json();
    let topCorrectText = 'Top 5 Most Correct:\n';
    stats.top_correct.forEach((q, index) => {
        topCorrectText += `${index + 1}. ${q.correct} pessoas acertaram a questão ${q.question_text.replace('?', '')}\n`;
    });
    document.getElementById('topCorrect').textContent = topCorrectText;

    let topIncorrectText = 'Top 5 Most Incorrect:\n';
    stats.top_incorrect.forEach((q, index) => {
        topIncorrectText += `${index + 1}. ${q.incorrect} pessoas erraram a questão ${q.question_text.replace('?', '')}\n`;
    });
    document.getElementById('topIncorrect').textContent = topIncorrectText;
}

async function showFastestUsers() {
    const response = await fetch('http://127.0.0.1:8000/fastest_users', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    });
    const fastestUsers = await response.json();
    let topFastestText = 'Top 5 Fastest Users:\n';
    fastestUsers.forEach((user, index) => {
        topFastestText += `${index + 1}. ${user.name} - ${user.time} seconds\n`;
    });
    document.getElementById('topFastest').textContent = topFastestText;
}

async function updateScores() {
    const response = await fetch(`http://127.0.0.1:8000/user_stats?user_id=${user_id}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    });
    const stats = await response.json();
    document.getElementById('correct-score').textContent = stats.correct;
    document.getElementById('incorrect-score').textContent = stats.incorrect;
    document.getElementById('abstention-score').textContent = stats.abstention;
}

function showNextQuestionTimer() {
    let nextQuestionTimeLeft = 5;
    const nextQuestionTimer = setInterval(() => {
        updateTimerChart(nextQuestionTimeLeft);
        nextQuestionTimeLeft--;
        if (nextQuestionTimeLeft < 0) {
            clearInterval(nextQuestionTimer);
            getQuestion();
        }
    }, 1000);
}

function createTimerChart() {
    const ctx = document.getElementById('timerChart').getContext('2d');
    timerChartConfig = {
        type: 'doughnut',
        data: {
            labels: ['Time Left'],
            datasets: [{
                data: [5, 0],
                backgroundColor: ['green', 'transparent'],
                borderWidth: 0
            }]
        },
        options: {
            circumference: 180,
            rotation: -90,
            cutout: '80%',
            plugins: {
                tooltip: {
                    enabled: false
                }
            }
        }
    };
    timerChart = new Chart(ctx, timerChartConfig);
}

function updateTimerChart(timeLeft) {
    const totalTime = 5;
    const percentage = timeLeft / totalTime;
    const color = `rgb(${255 - (percentage * 255)}, ${percentage * 255}, 0)`;
    timerChartConfig.data.datasets[0].data = [timeLeft, totalTime - timeLeft];
    timerChartConfig.data.datasets[0].backgroundColor = [color, 'transparent'];
    timerChart.update();
}

document.addEventListener('DOMContentLoaded', () => {
    createTimerChart();
});