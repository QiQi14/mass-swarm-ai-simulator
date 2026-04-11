export function initBottomSheet() {
  const sidebar = document.getElementById('sidebar');
  const handle = document.getElementById('bottom-sheet-handle');
  const overlayTriggerAreas = [handle, document.querySelector('.sidebar-header')];

  if (!sidebar) return;

  // Toggle expand on click
  overlayTriggerAreas.forEach(area => {
    if (area) {
      area.addEventListener('click', () => {
        if (window.innerWidth <= 768) {
          sidebar.classList.toggle('expanded');
        }
      });
    }
  });

  // Simple touch swipe detection
  let touchStartY = 0;
  let touchEndY = 0;

  sidebar.addEventListener('touchstart', (e) => {
    if (window.innerWidth > 768) return;
    // Don't interfere if they are trying to scroll inside a panel
    const target = e.target;
    const isScrollable = target.closest('.panel-scroll');
    // If they touch the handle or header, we track the swipe
    const isHeaderArea = target.closest('.bottom-sheet-handle') || target.closest('.sidebar-header');
    
    if (isHeaderArea) {
      touchStartY = e.changedTouches[0].screenY;
    } else {
      touchStartY = null;
    }
  }, { passive: true });

  sidebar.addEventListener('touchend', (e) => {
    if (window.innerWidth > 768 || touchStartY === null) return;
    
    touchEndY = e.changedTouches[0].screenY;
    handleSwipe();
  }, { passive: true });

  function handleSwipe() {
    const swipeDistance = touchEndY - touchStartY;
    const threshold = 50; // Minimum drag distance to trigger state change

    if (swipeDistance < -threshold) {
      // Swiped UP
      sidebar.classList.add('expanded');
    } else if (swipeDistance > threshold) {
      // Swiped DOWN
      sidebar.classList.remove('expanded');
    }
  }

  // Ensure sidebar resets if resized back to desktop
  window.addEventListener('resize', () => {
    if (window.innerWidth > 768) {
      sidebar.classList.remove('expanded');
    }
  });
}
