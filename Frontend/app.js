/**
 * YoutuLearn — Frontend Application
 * 
 * Handles:
 * - YouTube URL submission & video processing
 * - Chat interface with SSE streaming
 * - Timestamp rendering with clickable chips
 * - Conversation state management
 */

// ═══════════════════════════════════════════════════════════════
// Configuration
// ═══════════════════════════════════════════════════════════════

const API_BASE = window.location.origin;

// ═══════════════════════════════════════════════════════════════
// State
// ═══════════════════════════════════════════════════════════════

const state = {
    videoId: null,
    threadId: null,
    isProcessing: false,
    isChatting: false,
    messageHistory: [],
};

// ═══════════════════════════════════════════════════════════════
// DOM Elements
// ═══════════════════════════════════════════════════════════════

const dom = {
    // URL processing
    urlInput: document.getElementById('urlInput'),
    btnProcess: document.getElementById('btnProcess'),
    btnProcessText: document.getElementById('btnProcessText'),
    processSpinner: document.getElementById('processSpinner'),
    processingStatus: document.getElementById('processingStatus'),
    stepTranscript: document.getElementById('stepTranscript'),
    stepChunking: document.getElementById('stepChunking'),
    stepEmbedding: document.getElementById('stepEmbedding'),
    stepDone: document.getElementById('stepDone'),

    // Video info
    videoInfo: document.getElementById('videoInfo'),
    videoThumbnail: document.getElementById('videoThumbnail'),
    videoTitle: document.getElementById('videoTitle'),
    videoChunks: document.getElementById('videoChunks'),
    videoDuration: document.getElementById('videoDuration'),
    btnNewVideo: document.getElementById('btnNewVideo'),

    // Chat
    heroSection: document.getElementById('heroSection'),
    chatContainer: document.getElementById('chatContainer'),
    messagesArea: document.getElementById('messagesArea'),
    welcomeMessage: document.getElementById('welcomeMessage'),
    typingIndicator: document.getElementById('typingIndicator'),
    typingText: document.getElementById('typingText'),
    chatInput: document.getElementById('chatInput'),
    btnSend: document.getElementById('btnSend'),

    // Status
    statusDot: document.getElementById('statusDot'),
    statusText: document.getElementById('statusText'),

    // Toast
    toastContainer: document.getElementById('toastContainer'),

    // Quiz
    btnQuiz: document.getElementById('btnQuiz'),
    quizPanel: document.getElementById('quizPanel'),
    quizConfig: document.getElementById('quizConfig'),
    btnCloseQuiz: document.getElementById('btnCloseQuiz'),
    difficultySelector: document.getElementById('difficultySelector'),
    toggleMCQ: document.getElementById('toggleMCQ'),
    toggleShortAnswer: document.getElementById('toggleShortAnswer'),
    toggleFlashcard: document.getElementById('toggleFlashcard'),
    questionCount: document.getElementById('questionCount'),
    questionCountLabel: document.getElementById('questionCountLabel'),
    btnGenerateQuiz: document.getElementById('btnGenerateQuiz'),
    btnGenQuizText: document.getElementById('btnGenQuizText'),
    quizSpinner: document.getElementById('quizSpinner'),
    quizResults: document.getElementById('quizResults'),
    tabMCQ: document.getElementById('tabMCQ'),
    tabShort: document.getElementById('tabShort'),
    tabFlash: document.getElementById('tabFlash'),
    mcqCount: document.getElementById('mcqCount'),
    shortCount: document.getElementById('shortCount'),
    flashCount: document.getElementById('flashCount'),
    quizScore: document.getElementById('quizScore'),
    scoreFill: document.getElementById('scoreFill'),
    scoreText: document.getElementById('scoreText'),
    contentMCQ: document.getElementById('contentMCQ'),
    contentShort: document.getElementById('contentShort'),
    contentFlash: document.getElementById('contentFlash'),
    btnRegenQuiz: document.getElementById('btnRegenQuiz'),
    btnBackChat: document.getElementById('btnBackChat'),
};


// ═══════════════════════════════════════════════════════════════
// Event Listeners
// ═══════════════════════════════════════════════════════════════

dom.btnProcess.addEventListener('click', handleProcessVideo);
dom.urlInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleProcessVideo();
});

dom.btnSend.addEventListener('click', handleSendMessage);
dom.chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
    }
});

dom.chatInput.addEventListener('input', () => {
    dom.btnSend.disabled = !dom.chatInput.value.trim();
    autoResizeTextarea();
});

dom.btnNewVideo.addEventListener('click', resetToNewVideo);

// Suggestion chips
document.querySelectorAll('.suggestion-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
        const query = chip.getAttribute('data-query');
        dom.chatInput.value = query;
        dom.btnSend.disabled = false;
        handleSendMessage();
    });
});

// ── Quiz Event Listeners ────────────────────────────────────
dom.btnQuiz.addEventListener('click', showQuizPanel);
dom.btnCloseQuiz.addEventListener('click', hideQuizPanel);
dom.btnGenerateQuiz.addEventListener('click', handleGenerateQuiz);
dom.btnRegenQuiz.addEventListener('click', handleGenerateQuiz);
dom.btnBackChat.addEventListener('click', hideQuizPanel);

// Difficulty pills
dom.difficultySelector.querySelectorAll('.difficulty-pill').forEach((pill) => {
    pill.addEventListener('click', () => {
        dom.difficultySelector.querySelectorAll('.difficulty-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
    });
});

// Question count slider
dom.questionCount.addEventListener('input', () => {
    dom.questionCountLabel.textContent = dom.questionCount.value;
});

// Quiz tabs
[dom.tabMCQ, dom.tabShort, dom.tabFlash].forEach((tab) => {
    tab.addEventListener('click', () => switchQuizTab(tab.getAttribute('data-tab')));
});


// ═══════════════════════════════════════════════════════════════
// Video Processing
// ═══════════════════════════════════════════════════════════════

async function handleProcessVideo() {
    const url = dom.urlInput.value.trim();
    if (!url) {
        showToast('Please paste a YouTube URL', 'error');
        dom.urlInput.focus();
        return;
    }

    if (state.isProcessing) return;
    state.isProcessing = true;

    // UI: show loading
    dom.btnProcessText.textContent = 'Processing...';
    dom.processSpinner.style.display = 'block';
    dom.btnProcess.disabled = true;
    dom.processingStatus.classList.add('visible');

    // Animate steps
    setStepState('stepTranscript', 'active');

    try {
        const response = await fetch(`${API_BASE}/api/process`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });

        // Simulate step progression for UX
        setStepState('stepTranscript', 'done');
        setStepState('stepChunking', 'active');
        await sleep(300);
        setStepState('stepChunking', 'done');
        setStepState('stepEmbedding', 'active');
        await sleep(300);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to process video');
        }

        const data = await response.json();

        setStepState('stepEmbedding', 'done');
        setStepState('stepDone', 'active');
        await sleep(300);
        setStepState('stepDone', 'done');

        // Update state
        state.videoId = data.video_id;
        state.threadId = null;
        state.messageHistory = [];

        // Show video info
        showVideoInfo(data);

        // Transition to chat
        await sleep(500);
        transitionToChat();

        showToast(data.message || 'Video processed successfully!', 'success');
        setStatus('active', `Chatting about: ${data.title.substring(0, 30)}...`);

    } catch (error) {
        console.error('Process error:', error);
        showToast(error.message || 'Failed to process video', 'error');
        resetProcessingUI();
    } finally {
        state.isProcessing = false;
    }
}


// ═══════════════════════════════════════════════════════════════
// Chat
// ═══════════════════════════════════════════════════════════════

async function handleSendMessage() {
    const message = dom.chatInput.value.trim();
    if (!message || state.isChatting || !state.videoId) return;

    state.isChatting = true;
    dom.chatInput.value = '';
    dom.btnSend.disabled = true;
    autoResizeTextarea();

    // Hide welcome message
    if (dom.welcomeMessage) {
        dom.welcomeMessage.style.display = 'none';
    }

    // Add user message to UI
    addMessage('user', message);

    // Show typing indicator
    showTypingIndicator('Searching transcript...');

    try {
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                video_id: state.videoId,
                thread_id: state.threadId,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Chat request failed');
        }

        // Read SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Parse SSE events from buffer
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // Keep incomplete line in buffer

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.slice(6).trim();
                    if (!jsonStr) continue;

                    try {
                        const event = JSON.parse(jsonStr);
                        handleStreamEvent(event);
                    } catch (e) {
                        console.warn('Failed to parse SSE event:', jsonStr);
                    }
                }
            }
        }

    } catch (error) {
        console.error('Chat error:', error);
        hideTypingIndicator();
        addMessage('ai', `Sorry, an error occurred: ${error.message}. Please try again.`);
    } finally {
        state.isChatting = false;
        dom.btnSend.disabled = !dom.chatInput.value.trim();
    }
}


function handleStreamEvent(event) {
    switch (event.type) {
        case 'status':
            updateTypingText(getStatusMessage(event.node));
            break;

        case 'answer':
            hideTypingIndicator();
            addMessage('ai', event.content, event.timestamps || []);
            if (event.thread_id) {
                state.threadId = event.thread_id;
            }
            break;

        case 'error':
            hideTypingIndicator();
            addMessage('ai', `⚠️ Error: ${event.message}`);
            break;

        case 'done':
            hideTypingIndicator();
            break;
    }
}


function getStatusMessage(nodeName) {
    const messages = {
        'router': '🔀 Analyzing your question...',
        'retrieve': '🔍 Searching transcript...',
        'grade': '📊 Evaluating relevance...',
        'rewrite': '✏️ Refining search query...',
        'generate': '💡 Generating answer...',
        'direct': '💬 Composing response...',
    };
    return messages[nodeName] || `Processing: ${nodeName}...`;
}


// ═══════════════════════════════════════════════════════════════
// Message Rendering
// ═══════════════════════════════════════════════════════════════

function addMessage(role, content, timestamps = []) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message--${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message__avatar';
    avatar.textContent = role === 'user' ? '👤' : '🤖';

    const bubble = document.createElement('div');
    bubble.className = 'message__bubble';

    // Render content with formatting
    bubble.innerHTML = formatMessageContent(content);

    // Add timestamp chips if available
    if (timestamps.length > 0) {
        const tsContainer = document.createElement('div');
        tsContainer.className = 'timestamps-container';

        timestamps.forEach((ts) => {
            const chip = document.createElement('a');
            chip.className = 'timestamp-chip';
            chip.href = ts.url;
            chip.target = '_blank';
            chip.rel = 'noopener noreferrer';
            chip.title = ts.text;

            const startFmt = formatTime(ts.start_time);
            chip.innerHTML = `<span class="timestamp-chip__icon">▶</span>${startFmt}`;

            tsContainer.appendChild(chip);
        });

        bubble.appendChild(tsContainer);
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(bubble);

    dom.messagesArea.appendChild(messageDiv);
    scrollToBottom();

    // Track message
    state.messageHistory.push({ role, content });
}


function formatMessageContent(content) {
    if (!content) return '';

    let html = content;

    // Escape HTML except for our formatting
    html = html.replace(/&/g, '&amp;')
               .replace(/</g, '&lt;')
               .replace(/>/g, '&gt;');

    // Convert timestamp references like [1:23] or [01:23:45] to styled spans
    html = html.replace(
        /\[(\d{1,2}:\d{2}(?::\d{2})?)\]/g,
        (match, time) => {
            const seconds = timeToSeconds(time);
            const url = `https://www.youtube.com/watch?v=${state.videoId}&t=${seconds}s`;
            return `<a class="timestamp-chip" href="${url}" target="_blank" rel="noopener noreferrer"><span class="timestamp-chip__icon">▶</span>${time}</a>`;
        }
    );

    // Bold: **text**
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Code: `text`
    html = html.replace(/`(.*?)`/g, '<code style="background:rgba(139,92,246,0.15);padding:2px 6px;border-radius:4px;font-family:var(--font-mono);font-size:0.85em;">$1</code>');

    // Line breaks
    html = html.replace(/\n/g, '<br>');

    return html;
}


function formatTime(seconds) {
    const total = Math.floor(seconds);
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;

    if (h > 0) {
        return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }
    return `${m}:${s.toString().padStart(2, '0')}`;
}


function timeToSeconds(timeStr) {
    const parts = timeStr.split(':').map(Number);
    if (parts.length === 3) {
        return parts[0] * 3600 + parts[1] * 60 + parts[2];
    }
    return parts[0] * 60 + parts[1];
}


// ═══════════════════════════════════════════════════════════════
// UI Helpers
// ═══════════════════════════════════════════════════════════════

function showVideoInfo(data) {
    dom.videoTitle.textContent = data.title;
    dom.videoChunks.textContent = data.chunk_count;
    dom.videoDuration.textContent = data.duration_formatted;
    dom.videoThumbnail.src = `https://img.youtube.com/vi/${data.video_id}/mqdefault.jpg`;
    dom.videoInfo.classList.add('visible');
}


function transitionToChat() {
    // Fade out hero, show chat
    dom.heroSection.style.display = 'none';
    dom.chatContainer.classList.add('visible');
    dom.processingStatus.classList.remove('visible');
    dom.chatInput.focus();
}


function resetToNewVideo() {
    // Reset state
    state.videoId = null;
    state.threadId = null;
    state.messageHistory = [];

    // Reset UI
    dom.heroSection.style.display = '';
    dom.chatContainer.classList.remove('visible');
    dom.quizPanel.classList.remove('visible');
    dom.videoInfo.classList.remove('visible');
    dom.urlInput.value = '';
    resetProcessingUI();
    setStatus('', 'Ready');

    // Clear messages
    dom.messagesArea.innerHTML = '';
    const welcomeHtml = `
        <div class="welcome-message" id="welcomeMessage">
            <div class="welcome-message__icon">💬</div>
            <div class="welcome-message__text">
                Video processed! Ask anything about it.<br>
                I'll answer with exact timestamp references.
            </div>
            <div class="welcome-message__suggestions">
                <button class="suggestion-chip" data-query="What is this video about?">📋 What is this video about?</button>
                <button class="suggestion-chip" data-query="Summarize the key points">📝 Summarize key points</button>
                <button class="suggestion-chip" data-query="What are the main topics discussed?">🎯 Main topics discussed</button>
                <button class="suggestion-chip" data-query="Explain the most important concept">💡 Most important concept</button>
            </div>
        </div>
    `;
    dom.messagesArea.innerHTML = welcomeHtml;

    // Re-bind suggestion chips
    document.querySelectorAll('.suggestion-chip').forEach((chip) => {
        chip.addEventListener('click', () => {
            const query = chip.getAttribute('data-query');
            dom.chatInput.value = query;
            dom.btnSend.disabled = false;
            handleSendMessage();
        });
    });

    dom.urlInput.focus();
}


function resetProcessingUI() {
    dom.btnProcessText.textContent = '⚡ Process Video';
    dom.processSpinner.style.display = 'none';
    dom.btnProcess.disabled = false;
    dom.processingStatus.classList.remove('visible');

    // Reset all steps
    ['stepTranscript', 'stepChunking', 'stepEmbedding', 'stepDone'].forEach((id) => {
        document.getElementById(id).className = 'processing-status__step';
    });
}


function setStepState(stepId, status) {
    const el = document.getElementById(stepId);
    el.className = `processing-status__step ${status}`;
}


function showTypingIndicator(text = 'Thinking...') {
    dom.typingIndicator.classList.add('visible');
    dom.typingText.textContent = text;
    scrollToBottom();
}


function updateTypingText(text) {
    dom.typingText.textContent = text;
}


function hideTypingIndicator() {
    dom.typingIndicator.classList.remove('visible');
}


function setStatus(dotClass, text) {
    dom.statusDot.className = `status-dot ${dotClass}`;
    dom.statusText.textContent = text;
}


function scrollToBottom() {
    requestAnimationFrame(() => {
        dom.messagesArea.scrollTop = dom.messagesArea.scrollHeight;
    });
}


function autoResizeTextarea() {
    dom.chatInput.style.height = 'auto';
    dom.chatInput.style.height = Math.min(dom.chatInput.scrollHeight, 120) + 'px';
}


// ═══════════════════════════════════════════════════════════════
// Toast Notifications
// ═══════════════════════════════════════════════════════════════

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.textContent = message;

    dom.toastContainer.appendChild(toast);

    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}


// ═══════════════════════════════════════════════════════════════
// Utility
// ═══════════════════════════════════════════════════════════════

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}


// ═══════════════════════════════════════════════════════════════
// Quiz Feature
// ═══════════════════════════════════════════════════════════════

const quizState = {
    isGenerating: false,
    currentQuiz: null,
    mcqAnswered: 0,
    mcqCorrect: 0,
    mcqTotal: 0,
};


function showQuizPanel() {
    dom.chatContainer.classList.remove('visible');
    dom.quizPanel.classList.add('visible');
    dom.quizConfig.style.display = '';
    dom.quizResults.style.display = 'none';
}


function hideQuizPanel() {
    dom.quizPanel.classList.remove('visible');
    dom.chatContainer.classList.add('visible');
}


async function handleGenerateQuiz() {
    if (quizState.isGenerating || !state.videoId) return;
    quizState.isGenerating = true;

    // Get settings
    const difficulty = dom.difficultySelector.querySelector('.difficulty-pill.active')?.getAttribute('data-difficulty') || 'easy';
    const questionTypes = [];
    if (dom.toggleMCQ.checked) questionTypes.push('mcq');
    if (dom.toggleShortAnswer.checked) questionTypes.push('short_answer');
    if (dom.toggleFlashcard.checked) questionTypes.push('flashcard');

    if (questionTypes.length === 0) {
        showToast('Please select at least one question type', 'error');
        quizState.isGenerating = false;
        return;
    }

    const numQuestions = parseInt(dom.questionCount.value);

    // UI: Loading state
    dom.btnGenQuizText.textContent = 'Generating...';
    dom.quizSpinner.style.display = 'block';
    dom.btnGenerateQuiz.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/api/quiz/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                video_id: state.videoId,
                difficulty,
                question_types: questionTypes,
                num_questions: numQuestions,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate quiz');
        }

        const quiz = await response.json();
        quizState.currentQuiz = quiz;

        // Reset MCQ score
        quizState.mcqAnswered = 0;
        quizState.mcqCorrect = 0;
        quizState.mcqTotal = quiz.mcqs.length;

        // Render quiz
        renderQuizResults(quiz);

        showToast(`Quiz generated! ${quiz.total_questions} questions ready.`, 'success');

    } catch (error) {
        console.error('Quiz error:', error);
        showToast(error.message || 'Failed to generate quiz', 'error');
    } finally {
        quizState.isGenerating = false;
        dom.btnGenQuizText.textContent = '⚡ Generate Quiz';
        dom.quizSpinner.style.display = 'none';
        dom.btnGenerateQuiz.disabled = false;
    }
}


function renderQuizResults(quiz) {
    // Hide config, show results
    dom.quizConfig.style.display = 'none';
    dom.quizResults.style.display = '';

    // Update counts
    dom.mcqCount.textContent = quiz.mcqs.length;
    dom.shortCount.textContent = quiz.short_answers.length;
    dom.flashCount.textContent = quiz.flashcards.length;

    // Render MCQs
    dom.contentMCQ.innerHTML = '';
    quiz.mcqs.forEach((mcq, i) => {
        dom.contentMCQ.appendChild(renderMCQCard(mcq, i));
    });

    // Render Short Answers
    dom.contentShort.innerHTML = '';
    quiz.short_answers.forEach((sa, i) => {
        dom.contentShort.appendChild(renderShortAnswerCard(sa, i));
    });

    // Render Flashcards
    dom.contentFlash.innerHTML = '';
    quiz.flashcards.forEach((fc, i) => {
        dom.contentFlash.appendChild(renderFlashcard(fc, i));
    });

    // Set up score bar for MCQs
    if (quiz.mcqs.length > 0) {
        dom.quizScore.style.display = '';
        updateScoreBar();
    } else {
        dom.quizScore.style.display = 'none';
    }

    // Activate first tab that has content
    if (quiz.mcqs.length > 0) {
        switchQuizTab('mcq');
    } else if (quiz.short_answers.length > 0) {
        switchQuizTab('short');
    } else if (quiz.flashcards.length > 0) {
        switchQuizTab('flash');
    }
}


// ── MCQ Card ────────────────────────────────────────────────

function renderMCQCard(mcq, index) {
    const card = document.createElement('div');
    card.className = 'mcq-card';
    card.style.animationDelay = `${index * 0.05}s`;

    const letters = ['A', 'B', 'C', 'D'];
    const tsLink = mcq.timestamp
        ? `<a class="mcq-card__timestamp" href="https://www.youtube.com/watch?v=${state.videoId}&t=${timeToSeconds(mcq.timestamp)}s" target="_blank" rel="noopener noreferrer">⏱ ${mcq.timestamp}</a>`
        : '';

    card.innerHTML = `
        <div class="mcq-card__header">
            <span class="mcq-card__number">Q${index + 1}</span>
            ${tsLink}
        </div>
        <div class="mcq-card__question">${escapeHtml(mcq.question)}</div>
        <div class="mcq-card__options">
            ${mcq.options.map((opt, i) => `
                <div class="mcq-option" data-index="${i}" data-card="${index}">
                    <span class="mcq-option__letter">${letters[i]}</span>
                    <span>${escapeHtml(opt)}</span>
                </div>
            `).join('')}
        </div>
        <div class="mcq-card__explanation" id="mcqExplanation${index}">
            💡 ${escapeHtml(mcq.explanation)}
        </div>
    `;

    // Attach click handlers to options
    card.querySelectorAll('.mcq-option').forEach((opt) => {
        opt.addEventListener('click', () => handleMCQAnswer(card, mcq, parseInt(opt.getAttribute('data-index'))));
    });

    return card;
}


function handleMCQAnswer(card, mcq, selectedIndex) {
    const options = card.querySelectorAll('.mcq-option');

    // Check if already answered
    if (options[0].classList.contains('mcq-option--disabled')) return;

    const correctIndex = mcq.correct_answer_index;
    const isCorrect = selectedIndex === correctIndex;

    // Mark all as disabled
    options.forEach((opt, i) => {
        opt.classList.add('mcq-option--disabled');
        if (i === correctIndex) {
            opt.classList.add('mcq-option--correct');
        }
        if (i === selectedIndex && !isCorrect) {
            opt.classList.add('mcq-option--wrong');
        }
    });

    // Show explanation
    const explanation = card.querySelector('.mcq-card__explanation');
    if (explanation) {
        explanation.classList.add('visible');
    }

    // Update score
    quizState.mcqAnswered++;
    if (isCorrect) quizState.mcqCorrect++;
    updateScoreBar();
}


function updateScoreBar() {
    const total = quizState.mcqTotal;
    const correct = quizState.mcqCorrect;
    const answered = quizState.mcqAnswered;

    const pct = total > 0 ? (correct / total) * 100 : 0;
    dom.scoreFill.style.width = `${pct}%`;
    dom.scoreText.textContent = `${correct} / ${total} correct${answered < total ? ` (${total - answered} left)` : ''}`;
}


// ── Short Answer Card ───────────────────────────────────────

function renderShortAnswerCard(sa, index) {
    const card = document.createElement('div');
    card.className = 'sa-card';
    card.style.animationDelay = `${index * 0.05}s`;

    const tsLink = sa.timestamp
        ? `<a class="sa-card__timestamp" href="https://www.youtube.com/watch?v=${state.videoId}&t=${timeToSeconds(sa.timestamp)}s" target="_blank" rel="noopener noreferrer">⏱ ${sa.timestamp}</a>`
        : '';

    const keyPointsHtml = sa.key_points && sa.key_points.length > 0
        ? `<ul class="sa-card__key-points">${sa.key_points.map(kp => `<li>${escapeHtml(kp)}</li>`).join('')}</ul>`
        : '';

    card.innerHTML = `
        <div class="sa-card__header">
            <span class="sa-card__number">Q${index + 1}</span>
            ${tsLink}
        </div>
        <div class="sa-card__question">${escapeHtml(sa.question)}</div>
        <button class="sa-card__reveal-btn">👁 Show Answer</button>
        <div class="sa-card__answer" id="saAnswer${index}">
            <div class="sa-card__answer-label">Model Answer</div>
            <div class="sa-card__answer-text">${escapeHtml(sa.model_answer)}</div>
            ${keyPointsHtml}
        </div>
    `;

    // Reveal button
    const btn = card.querySelector('.sa-card__reveal-btn');
    const answer = card.querySelector('.sa-card__answer');
    btn.addEventListener('click', () => {
        const isVisible = answer.classList.contains('visible');
        answer.classList.toggle('visible');
        btn.textContent = isVisible ? '👁 Show Answer' : '🙈 Hide Answer';
    });

    return card;
}


// ── Flashcard ───────────────────────────────────────────────

function renderFlashcard(fc, index) {
    const wrapper = document.createElement('div');
    wrapper.className = 'flashcard-wrapper';
    wrapper.style.animationDelay = `${index * 0.05}s`;

    const tsLink = fc.timestamp
        ? `<a class="flashcard__timestamp" href="https://www.youtube.com/watch?v=${state.videoId}&t=${timeToSeconds(fc.timestamp)}s" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()">⏱ ${fc.timestamp}</a>`
        : '';

    wrapper.innerHTML = `
        <div class="flashcard" data-index="${index}">
            <div class="flashcard__face flashcard__front">
                <span class="flashcard__number">${index + 1}</span>
                ${tsLink}
                <div class="flashcard__label">Question</div>
                <div class="flashcard__text">${escapeHtml(fc.front)}</div>
                <div class="flashcard__hint">Click to flip</div>
            </div>
            <div class="flashcard__face flashcard__back">
                <span class="flashcard__number">${index + 1}</span>
                <div class="flashcard__label">Answer</div>
                <div class="flashcard__text">${escapeHtml(fc.back)}</div>
                <div class="flashcard__hint">Click to flip back</div>
            </div>
        </div>
    `;

    // Flip on click
    const flashcard = wrapper.querySelector('.flashcard');
    flashcard.addEventListener('click', () => {
        flashcard.classList.toggle('flipped');
    });

    return wrapper;
}


// ── Tab Switching ───────────────────────────────────────────

function switchQuizTab(tabName) {
    // Update tab buttons
    [dom.tabMCQ, dom.tabShort, dom.tabFlash].forEach(t => t.classList.remove('active'));
    [dom.contentMCQ, dom.contentShort, dom.contentFlash].forEach(c => c.classList.remove('active'));

    switch (tabName) {
        case 'mcq':
            dom.tabMCQ.classList.add('active');
            dom.contentMCQ.classList.add('active');
            dom.quizScore.style.display = quizState.mcqTotal > 0 ? '' : 'none';
            break;
        case 'short':
            dom.tabShort.classList.add('active');
            dom.contentShort.classList.add('active');
            dom.quizScore.style.display = 'none';
            break;
        case 'flash':
            dom.tabFlash.classList.add('active');
            dom.contentFlash.classList.add('active');
            dom.quizScore.style.display = 'none';
            break;
    }
}


// ── HTML Escape Helper ──────────────────────────────────────

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;');
}
