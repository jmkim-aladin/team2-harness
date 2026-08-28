document.querySelectorAll('.copy').forEach((button) => {
  button.addEventListener('click', async () => {
    const code = button.closest('.code-block').querySelector('code').innerText;
    await navigator.clipboard.writeText(code);
    const previous = button.textContent;
    button.textContent = '복사됨';
    setTimeout(() => { button.textContent = previous; }, 1200);
  });
});

document.querySelectorAll('[data-quiz]').forEach((quiz) => {
  const feedback = quiz.querySelector('.quiz-feedback');
  quiz.querySelectorAll('button[data-answer]').forEach((button) => {
    button.addEventListener('click', () => {
      const correct = button.dataset.answer === 'correct';
      feedback.textContent = correct ? quiz.dataset.correctFeedback : quiz.dataset.wrongFeedback;
      feedback.className = `quiz-feedback ${correct ? 'correct' : 'wrong'}`;
    });
  });
});

document.querySelectorAll('[data-checklist]').forEach((list) => {
  const key = `teach:${location.pathname}:${list.dataset.checklist}`;
  const boxes = [...list.querySelectorAll('input[type="checkbox"]')];
  const saved = JSON.parse(localStorage.getItem(key) || '[]');
  boxes.forEach((box, index) => {
    box.checked = Boolean(saved[index]);
    box.addEventListener('change', () => {
      localStorage.setItem(key, JSON.stringify(boxes.map((item) => item.checked)));
    });
  });
});
