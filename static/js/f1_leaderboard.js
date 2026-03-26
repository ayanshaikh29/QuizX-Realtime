/**
 * 🏎️ QuizX Premium Green-White Leaderboard Manager
 * Handles real-time rank diffing, translateY transforms, and premium overtake notifications.
 */
class F1Leaderboard {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.rows = new Map(); // student -> element
        this.prevRanks = new Map(); // student -> rank
        this.rowHeight = 72; // Synchronized with user's updated CSS
    }

    update(leaderboardData, lastSubmitter, isFinal = false) {
        if (!this.container) return;

        const listContainer = this.container.querySelector('.f1-list');
        const podiumContainer = document.getElementById('podiumContainer'); // Optional podium container
        if (!listContainer) return;

        // If final, handle Podium
        if (isFinal && podiumContainer) {
            this.renderPodium(leaderboardData.slice(0, 3));
            leaderboardData = leaderboardData.slice(3); // Rest go to list
            this.container.style.marginTop = "0";
        }

        // Set container height based on data
        listContainer.style.height = `${leaderboardData.length * this.rowHeight}px`;

        // Calculate max points for progress bars
        const maxPoints = leaderboardData.length > 0 ? Math.max(...leaderboardData.map(e => e.points), 1) : 1;

        leaderboardData.forEach((entry, index) => {
            const rank = isFinal ? (index + 4) : (index + 1);
            const student = entry.student;
            const prevRank = this.prevRanks.get(student);

            let row = this.rows.get(student);

            // 1. Create row if it doesn't exist
            if (!row) {
                row = this.createRow(entry);
                listContainer.appendChild(row);
                this.rows.set(student, row);
            }

            // 2. Update entry data
            row.dataset.rank = rank;

            // Update Rank Change Indicator
            const rankChangeEl = row.querySelector('.rank-change');
            if (prevRank && !isFinal) {
                if (rank < prevRank) {
                    rankChangeEl.innerHTML = '<i class="fas fa-caret-up rank-up"></i>';
                } else if (rank > prevRank) {
                    rankChangeEl.innerHTML = '<i class="fas fa-caret-down rank-down"></i>';
                } else {
                    rankChangeEl.innerHTML = '<span class="rank-same">—</span>';
                }
            } else {
                rankChangeEl.innerHTML = '<span class="rank-same">—</span>';
            }

            // Update Rank Number
            row.querySelector('.rank-num').textContent = `#${rank}`;

            // Update Name Section
            const nameEl = row.querySelector('.f1-name');
            nameEl.innerHTML = `
                ${rank === 1 ? '<i class="fas fa-crown crown-icon"></i>' : ''}
                ${this.escapeHtml(student)}
                ${entry.is_fastest && !isFinal ? '<span class="fastest-badge"><i class="fas fa-bolt"></i> ⚡</span>' : ''}
            `;

            // Update Score & Progress Bar
            row.querySelector('.score-val').textContent = entry.points;
            const progress = (entry.points / maxPoints) * 100;
            row.querySelector('.score-progress-bar').style.width = `${progress}%`;

            // 3. Move row using GPU-accelerated translate
            row.style.transform = `translateY(${index * this.rowHeight}px)`;

            // 4. Handle Overtake Effect
            if (prevRank && rank < prevRank && !isFinal) {
                row.classList.add('just-overtook');
                setTimeout(() => row.classList.remove('just-overtook'), 1500);

                // Show toast if this specific student just overtook someone
                if (student === lastSubmitter) {
                    this.showOvertakeToast(student, rank);
                }
            }

            this.prevRanks.set(student, rank);
        });

        // 5. Cleanup disconnected students
        const currentStudents = new Set(leaderboardData.map(e => e.student));
        for (let [student, row] of this.rows) {
            if (!currentStudents.has(student)) {
                row.style.opacity = '0';
                row.style.transform += ' scale(0.9)';
                setTimeout(() => {
                    row.remove();
                    this.rows.delete(student);
                    this.prevRanks.delete(student);
                }, 700);
            }
        }
    }

    createRow(entry) {
        const row = document.createElement('div');
        row.className = 'f1-row';
        row.innerHTML = `
            <div class="rank-box">
                <span class="rank-num"></span>
            </div>
            <div class="f1-info">
                <div class="f1-name-section" style="width: 100%;">
                    <div class="f1-name"></div>
                    <div class="score-progress-container">
                        <div class="score-progress-bar"></div>
                    </div>
                </div>
            </div>
            <div class="rank-change"></div>
            <div class="score-pill">
                <span class="score-val"></span> <span style="font-size: 0.6rem; opacity: 0.7;">pts</span>
            </div>
        `;
        return row;
    }

    renderPodium(top3) {
        const podiumContainer = document.getElementById('podiumContainer');
        if (!podiumContainer) return;
        podiumContainer.innerHTML = '';

        let displayOrder = [];
        if (top3.length === 1) displayOrder = [top3[0]];
        else if (top3.length === 2) displayOrder = [top3[1], top3[0]];
        else if (top3.length === 3) displayOrder = [top3[1], top3[0], top3[2]];

        displayOrder.forEach((p, i) => {
            const actualRank = top3.indexOf(p) + 1;
            const initials = p.student.substring(0, 2).toUpperCase();
            const card = document.createElement('div');
            card.className = `podium-card rank-${actualRank} animate__animated animate__fadeInUp`;
            card.style.animationDelay = `${i * 0.1}s`;
            card.innerHTML = `
                ${actualRank === 1 ? '<div class="crown-icon" style="margin-bottom: 5px;"><i class="fas fa-crown"></i></div>' : ''}
                <div class="podium-avatar">${initials}</div>
                <div class="podium-name">${this.escapeHtml(p.student)}</div>
                <div class="podium-score">${p.points} PTS</div>
                <div class="podium-badge">P${actualRank}</div>
            `;
            podiumContainer.appendChild(card);
        });
    }

    showOvertakeToast(student, newRank) {
        const existing = document.querySelector('.f1-toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = 'f1-toast';
        toast.innerHTML = `
            <i class="fas fa-rocket"></i>
            <div class="toast-content">
                <div class="toast-name">${this.escapeHtml(student)}</div>
                <div class="toast-msg">MOVED UP TO POSITION P${newRank}</div>
            </div>
        `;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.transform = 'translateY(-20px) scale(0.9)';
            toast.style.opacity = '0';
            toast.style.transition = 'all 0.5s ease';
            setTimeout(() => toast.remove(), 500);
        }, 3000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
