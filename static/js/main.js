// Korean Open Banking Accounting System - Main JavaScript
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * 앱 초기화
 */
function initializeApp() {
    // Feather Icons 초기화
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
    
    // 툴팁 초기화
    initializeTooltips();
    
    // 차트 기본 설정
    initializeChartDefaults();
    
    // 날짜 필터 초기화
    initializeDateFilters();
    
    // 키보드 단축키 설정
    setupKeyboardShortcuts();
    
    // 자동 새로고침 설정
    setupAutoRefresh();
}

/**
 * Bootstrap 툴팁 초기화
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Chart.js 기본 설정
 */
function initializeChartDefaults() {
    if (typeof Chart !== 'undefined') {
        Chart.defaults.font.family = "'Noto Sans KR', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
        Chart.defaults.font.size = 12;
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.padding = 20;
        
        // 한국어 로케일 설정
        Chart.defaults.locale = 'ko-KR';
    }
}

/**
 * 날짜 필터 기본값 설정
 */
function initializeDateFilters() {
    const today = new Date();
    const lastMonth = new Date();
    lastMonth.setMonth(today.getMonth() - 1);
    
    // 시작일/종료일 필드가 있으면 기본값 설정
    const startDateField = document.getElementById('startDate');
    const endDateField = document.getElementById('endDate');
    
    if (startDateField && !startDateField.value) {
        startDateField.value = lastMonth.toISOString().split('T')[0];
    }
    
    if (endDateField && !endDateField.value) {
        endDateField.value = today.toISOString().split('T')[0];
    }
}

/**
 * 키보드 단축키 설정
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K: 검색 포커스
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('input[type="search"], input[name="search"]');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Ctrl/Cmd + R: 새로고침 (기본 동작 유지)
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            // 기본 새로고침 허용
        }
        
        // ESC: 모달 닫기
        if (e.key === 'Escape') {
            const openModal = document.querySelector('.modal.show');
            if (openModal) {
                const modal = bootstrap.Modal.getInstance(openModal);
                if (modal) {
                    modal.hide();
                }
            }
        }
    });
}

/**
 * 자동 새로고침 설정 (선택적)
 */
function setupAutoRefresh() {
    // 대시보드에서만 자동 새로고침 활성화
    if (window.location.pathname === '/' || window.location.pathname === '/dashboard') {
        // 5분마다 KPI 데이터만 새로고침
        setInterval(function() {
            refreshKPIData();
        }, 5 * 60 * 1000); // 5분
    }
}

/**
 * KPI 데이터 새로고침
 */
function refreshKPIData() {
    // 실제로는 AJAX 호출로 서버에서 최신 데이터 가져옴
    console.log('KPI 데이터 새로고침 중...');
    
    // 시뮬레이션: 페이지 전체 새로고침 대신 데이터만 업데이트
    // fetch('/api/kpi-data')
    //     .then(response => response.json())
    //     .then(data => updateKPICards(data))
    //     .catch(error => console.error('KPI 데이터 업데이트 실패:', error));
}

/**
 * 통화 포맷팅
 * @param {number} amount - 금액
 * @returns {string} - 포맷된 금액
 */
function formatCurrency(amount) {
    if (amount == null || isNaN(amount)) {
        return '0원';
    }
    return new Intl.NumberFormat('ko-KR').format(Math.abs(amount)) + '원';
}

/**
 * 날짜 포맷팅
 * @param {Date|string} date - 날짜
 * @param {string} format - 포맷 ('short', 'long', 'time')
 * @returns {string} - 포맷된 날짜
 */
function formatDate(date, format = 'short') {
    if (!date) return '';
    
    const d = new Date(date);
    if (isNaN(d.getTime())) return '';
    
    const options = {
        short: { year: 'numeric', month: '2-digit', day: '2-digit' },
        long: { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' },
        time: { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }
    };
    
    return new Intl.DateTimeFormat('ko-KR', options[format] || options.short).format(d);
}

/**
 * 토스트 메시지 표시
 * @param {string} message - 메시지 내용
 * @param {string} type - 메시지 타입 ('success', 'error', 'warning', 'info')
 * @param {number} duration - 표시 시간 (ms)
 */
function showToast(message, type = 'success', duration = 3000) {
    // 기존 토스트 제거
    const existingToast = document.querySelector('.toast-message');
    if (existingToast) {
        existingToast.remove();
    }
    
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} toast-message position-fixed top-0 end-0 m-3`;
    toast.style.zIndex = '9999';
    toast.style.minWidth = '300px';
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close ms-2" onclick="this.parentElement.remove()"></button>
    `;
    
    document.body.appendChild(toast);
    
    // 자동 제거
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, duration);
}

/**
 * 로딩 상태 표시/숨기기
 * @param {boolean} show - 표시 여부
 * @param {string} target - 대상 요소 선택자
 */
function toggleLoading(show, target = 'body') {
    const targetElement = document.querySelector(target);
    if (!targetElement) return;
    
    const loadingId = 'loading-overlay';
    let loadingOverlay = document.getElementById(loadingId);
    
    if (show) {
        if (!loadingOverlay) {
            loadingOverlay = document.createElement('div');
            loadingOverlay.id = loadingId;
            loadingOverlay.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center';
            loadingOverlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
            loadingOverlay.style.zIndex = '9998';
            loadingOverlay.innerHTML = `
                <div class="text-center text-white">
                    <div class="spinner-border mb-3" role="status">
                        <span class="visually-hidden">로딩 중...</span>
                    </div>
                    <div>처리 중입니다...</div>
                </div>
            `;
            document.body.appendChild(loadingOverlay);
        }
    } else {
        if (loadingOverlay) {
            loadingOverlay.remove();
        }
    }
}

/**
 * 폼 데이터를 JSON으로 변환
 * @param {HTMLFormElement} form - 폼 요소
 * @returns {Object} - JSON 객체
 */
function formToJSON(form) {
    const formData = new FormData(form);
    const json = {};
    
    for (let [key, value] of formData.entries()) {
        // 체크박스 처리
        if (form.elements[key] && form.elements[key].type === 'checkbox') {
            json[key] = form.elements[key].checked;
        } else {
            json[key] = value;
        }
    }
    
    return json;
}

/**
 * 테이블 정렬 기능
 * @param {HTMLTableElement} table - 테이블 요소
 * @param {number} columnIndex - 정렬할 컬럼 인덱스
 * @param {string} type - 데이터 타입 ('string', 'number', 'date')
 */
function sortTable(table, columnIndex, type = 'string') {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // 현재 정렬 방향 확인
    const header = table.querySelectorAll('th')[columnIndex];
    const isAscending = !header.classList.contains('sort-desc');
    
    // 헤더 클래스 업데이트
    table.querySelectorAll('th').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    header.classList.add(isAscending ? 'sort-asc' : 'sort-desc');
    
    // 행 정렬
    rows.sort((a, b) => {
        const aVal = a.cells[columnIndex].textContent.trim();
        const bVal = b.cells[columnIndex].textContent.trim();
        
        let comparison = 0;
        
        switch (type) {
            case 'number':
                const aNum = parseFloat(aVal.replace(/[^0-9.-]/g, ''));
                const bNum = parseFloat(bVal.replace(/[^0-9.-]/g, ''));
                comparison = aNum - bNum;
                break;
            case 'date':
                comparison = new Date(aVal) - new Date(bVal);
                break;
            default:
                comparison = aVal.localeCompare(bVal, 'ko-KR');
        }
        
        return isAscending ? comparison : -comparison;
    });
    
    // 정렬된 행 재배치
    rows.forEach(row => tbody.appendChild(row));
}

/**
 * 검색 필터 적용
 * @param {string} searchTerm - 검색어
 * @param {string} tableSelector - 테이블 선택자
 * @param {Array} searchColumns - 검색할 컬럼 인덱스 배열
 */
function filterTable(searchTerm, tableSelector, searchColumns = []) {
    const table = document.querySelector(tableSelector);
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    const rows = tbody.querySelectorAll('tr');
    
    const term = searchTerm.toLowerCase();
    
    rows.forEach(row => {
        let found = false;
        
        if (searchColumns.length === 0) {
            // 모든 컬럼에서 검색
            found = row.textContent.toLowerCase().includes(term);
        } else {
            // 지정된 컬럼에서만 검색
            for (let colIndex of searchColumns) {
                if (row.cells[colIndex] && row.cells[colIndex].textContent.toLowerCase().includes(term)) {
                    found = true;
                    break;
                }
            }
        }
        
        row.style.display = found ? '' : 'none';
    });
}

/**
 * 파일 다운로드
 * @param {string} url - 다운로드 URL
 * @param {string} filename - 파일명
 */
function downloadFile(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * 클립보드에 텍스트 복사
 * @param {string} text - 복사할 텍스트
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showToast('클립보드에 복사되었습니다.', 'success', 2000);
    }).catch(function() {
        // 폴백: textarea 사용
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast('클립보드에 복사되었습니다.', 'success', 2000);
    });
}

/**
 * 디바운스 함수
 * @param {Function} func - 실행할 함수
 * @param {number} wait - 대기 시간 (ms)
 * @returns {Function} - 디바운스된 함수
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * 쓰로틀 함수
 * @param {Function} func - 실행할 함수
 * @param {number} limit - 제한 시간 (ms)
 * @returns {Function} - 쓰로틀된 함수
 */
function throttle(func, limit) {
    let inThrottle;
    return function executedFunction(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * 로컬 스토리지 헬퍼
 */
const Storage = {
    set: function(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (e) {
            console.error('localStorage set error:', e);
            return false;
        }
    },
    
    get: function(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.error('localStorage get error:', e);
            return defaultValue;
        }
    },
    
    remove: function(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (e) {
            console.error('localStorage remove error:', e);
            return false;
        }
    },
    
    clear: function() {
        try {
            localStorage.clear();
            return true;
        } catch (e) {
            console.error('localStorage clear error:', e);
            return false;
        }
    }
};

/**
 * API 호출 헬퍼 (향후 AJAX 요청용)
 */
const API = {
    get: function(url) {
        return fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        }).then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        });
    },
    
    post: function(url, data) {
        return fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        }).then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        });
    }
};

// 글로벌 유틸리티 함수들을 window 객체에 추가
window.showToast = showToast;
window.toggleLoading = toggleLoading;
window.formatCurrency = formatCurrency;
window.formatDate = formatDate;
window.copyToClipboard = copyToClipboard;
window.Storage = Storage;
window.API = API;
