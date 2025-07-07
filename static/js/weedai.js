// Store all star counts from database
let allStarCounts = {};

// Fetch leaderboard data
async function fetchLeaderboard() {
  const res = await fetch('/.netlify/functions/leaderboard');
  if (!res.ok) return;
  const data = await res.json();
  const ol = document.getElementById('leaderboard-list');
  ol.innerHTML = '';
  data.forEach(item => {
    const li = document.createElement('li');
    li.textContent = `${item.dataset_name} (${item.stars} ⭐)`;
    ol.appendChild(li);
  });
}

// Handle star button clicks - pass the button element
window.recordStar = async function(button) {
  // Get the dataset name from the parent popup div
  const popup = button.closest('.dataset-popup');
  const datasetName = popup.getAttribute('data-name');

  const keyStarred = 'starred_' + datasetName;
  if (localStorage.getItem(keyStarred)) return;

  // Update UI
  localStorage.setItem(keyStarred, '1');
  button.disabled = true;

  // Update count
  const countSpan = popup.querySelector('.star-count');
  const currentCount = parseInt(countSpan.textContent) || 0;
  countSpan.textContent = currentCount + 1;

  // Send to server
  await fetch('/.netlify/functions/star', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ name: datasetName })
  });

  // Refresh leaderboard
  fetchLeaderboard();
}

// When page loads
document.addEventListener('DOMContentLoaded', async () => {
  // Get all counts
  try {
    const resp = await fetch('/.netlify/functions/counts');
    if (resp.ok) {
      allStarCounts = await resp.json();
    }
  } catch (e) {
    console.error('Error:', e);
  }

  // Update leaderboard
  fetchLeaderboard();

  // Watch for popups being added to the page
  document.addEventListener('click', function() {
    // After any click, check if there are popups that need updating
    setTimeout(() => {
      document.querySelectorAll('.dataset-popup').forEach(popup => {
        const name = popup.getAttribute('data-name');
        const countSpan = popup.querySelector('.star-count');
        const button = popup.querySelector('.star-btn');

        // Update count if we have data for this dataset
        if (allStarCounts[name] && countSpan.textContent === '0') {
          countSpan.textContent = allStarCounts[name];
        }

        // Disable button if already starred
        if (localStorage.getItem('starred_' + name)) {
          button.disabled = true;
        }
      });
    }, 100);
  });

  // Toggle button
  const sidebar = document.getElementById('leaderboard');
  const btn = document.getElementById('toggle-leaderboard');
  if (btn && sidebar) {
    btn.addEventListener('click', () => {
      if (sidebar.style.display === 'none' || sidebar.style.display === '') {
        sidebar.style.display = 'block';
        btn.textContent = 'Hide Leaderboard';
      } else {
        sidebar.style.display = 'none';
        btn.textContent = 'Show Leaderboard';
      }
    });
  }
});