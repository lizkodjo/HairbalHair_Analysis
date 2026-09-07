// DOM Elements
const conditionsGrid = document.getElementById('conditionsGrid');
const selectedList = document.getElementById('selectedConditionsList');
const getBtn = document.getElementById('getRecommendationsBtn');
const getDetailedBtn = document.getElementById('getDetailedBtn');
const resultsSection = document.getElementById('resultsSection');
const loadingSpinner = document.getElementById('loadingSpinner');

//  State 
let selectedConditions = [];
let allConditions = [];
let selectedFile = null;

//  Button State Management 

function updateButtons() {
    // Button is enabled if ANY conditions are selected (image is optional)
    const hasConditions = selectedConditions.length > 0;
    
    if (getBtn) {
        getBtn.disabled = !hasConditions;
        // Update button text to show image status
        const btnText = getBtn.querySelector('#btnText');
        if (btnText) {
            if (selectedFile) {
                btnText.textContent = 'Analyze with Image';
            } else {
                btnText.textContent = 'Get Herb Recommendations';
            }
        }
    }
    
    if (getDetailedBtn) {
        getDetailedBtn.disabled = !hasConditions;
    }
}

//  Image Upload Handlers 

const uploadArea = document.getElementById('uploadArea');
const imageInput = document.getElementById('imageInput');
const imagePreview = document.getElementById('imagePreview');
const previewImg = document.getElementById('previewImg');

if (uploadArea) {
    uploadArea.addEventListener('click', () => {
        if (imageInput) imageInput.click();
    });
    
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });
}

if (imageInput) {
    imageInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });
}

function handleFileSelect(file) {
    // Validate file type
    const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
        alert('Please upload a valid image (JPG, PNG, or WEBP)');
        return;
    }
    
    // Validate file size (16MB)
    if (file.size > 16 * 1024 * 1024) {
        alert('File size must be less than 16MB');
        return;
    }
    
    selectedFile = file;
    
    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImg.src = e.target.result;
        imagePreview.style.display = 'block';
        
        // Update upload area
        if (uploadArea) {
            uploadArea.innerHTML = `
                <i class="fas fa-check-circle" style="color: #4a7c2e; font-size: 48px;"></i>
                <p style="color: #2d5016; font-weight: 600;">Image ready: ${file.name}</p>
                <small>Click to change</small>
            `;
        }
        
        // Update button state
        updateButtons();
    };
    reader.readAsDataURL(file);
}

//  Load Conditions 

async function loadConditions() {
    try {
        const response = await fetch('/api/conditions');
        const data = await response.json();
        
        if (data.success && data.conditions) {
            allConditions = data.conditions;
            renderConditions(allConditions);
        }
    } catch (error) {
        console.error('Error loading conditions:', error);
        // Fallback conditions
        const fallback = [
            {id: 'hair_growth', name: 'Hair Growth', icon: '🌱'},
            {id: 'hair_fall', name: 'Hair Fall', icon: '💧'},
            {id: 'dandruff', name: 'Dandruff', icon: '🧴'},
            {id: 'dry_hair', name: 'Dry Hair', icon: '🏜️'},
            {id: 'oily_scalp', name: 'Oily Scalp', icon: '💦'}
        ];
        allConditions = fallback;
        renderConditions(fallback);
    }
}

function renderConditions(conditions) {
    if (!conditionsGrid) return;
    conditionsGrid.innerHTML = '';
    
    conditions.forEach(condition => {
        const chip = document.createElement('div');
        chip.className = 'condition-chip';
        chip.dataset.condition = condition.id;
        // <span class="icon">${condition.icon || '🌿'}</span>
        chip.innerHTML = `
            
            ${condition.name}
        `;
        chip.addEventListener('click', () => toggleCondition(condition.id, chip));
        conditionsGrid.appendChild(chip);
    });
}

function toggleCondition(conditionId, chip) {
    const index = selectedConditions.indexOf(conditionId);
    
    if (index === -1) {
        selectedConditions.push(conditionId);
        chip.classList.add('selected');
    } else {
        selectedConditions.splice(index, 1);
        chip.classList.remove('selected');
    }
    
    updateSelectedDisplay();
    updateButtons();
}

function updateSelectedDisplay() {
    if (!selectedList) return;
    
    if (selectedConditions.length === 0) {
        selectedList.innerHTML = '<span class="empty-message">No conditions selected yet</span>';
        return;
    }
    
    selectedList.innerHTML = '';
    selectedConditions.forEach(conditionId => {
        // Find condition name
        const condition = allConditions.find(c => c.id === conditionId);
        const displayName = condition ? condition.name : conditionId.replace(/_/g, ' ').title();
        const icon = condition ? condition.icon : '🌿';
        
        const tag = document.createElement('span');
        tag.className = 'condition-tag';
        tag.innerHTML = `${icon} ${displayName} <span class="remove-tag" data-condition="${conditionId}">×</span>`;
        tag.querySelector('.remove-tag').addEventListener('click', (e) => {
            const cond = e.target.dataset.condition;
            removeCondition(cond);
        });
        selectedList.appendChild(tag);
    });
}

function removeCondition(conditionId) {
    selectedConditions = selectedConditions.filter(c => c !== conditionId);
    
    // Update chips
    document.querySelectorAll('.condition-chip').forEach(chip => {
        if (chip.dataset.condition === conditionId) {
            chip.classList.remove('selected');
        }
    });
    
    updateSelectedDisplay();
    updateButtons();
}

//  Get Recommendations 

async function getRecommendations(detailed = false) {
    if (selectedConditions.length === 0) {
        alert('Please select at least one condition');
        return;
    }
    
    // Show loading
    if (loadingSpinner) loadingSpinner.style.display = 'block';
    if (getBtn) getBtn.disabled = true;
    if (getDetailedBtn) getDetailedBtn.disabled = true;
    if (resultsSection) resultsSection.style.display = 'none';
    
    try {
        let response;
        let data;
        
        // If image is selected, use the predict endpoint
        if (selectedFile) {
            const formData = new FormData();
            formData.append('image', selectedFile);
            formData.append('conditions', selectedConditions.join(','));
            
            console.log('📸 Analyzing with image...');
            response = await fetch('/api/predict', {
                method: 'POST',
                body: formData
            });
        } else {
            // Otherwise use the recommend endpoint
            const endpoint = detailed ? '/api/recommend/detailed' : '/api/recommend';
            console.log('📋 Getting recommendations without image...');
            response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    conditions: selectedConditions,
                    limit: 8,
                    include_ai: true
                })
            });
        }
        
        data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to get recommendations');
        }
        
        console.log('✅ Results received:', data);
        displayResults(data, detailed);
        
    } catch (error) {
        console.error('Error:', error);
        alert('Error getting recommendations: ' + error.message);
    } finally {
        if (loadingSpinner) loadingSpinner.style.display = 'none';
        if (getBtn) getBtn.disabled = false;
        if (getDetailedBtn) getDetailedBtn.disabled = false;
    }
}

//  Display Results 

function displayResults(data, detailed) {
    if (!resultsSection) return;
    resultsSection.style.display = 'block';
    
    // Show mode info
    const modeInfo = document.createElement('div');
    modeInfo.className = 'mode-info';
    if (data.mode === 'image-analysis') {
        modeInfo.innerHTML = `
            <div style="background: #e8f5e8; padding: 10px 15px; border-radius: 8px; margin-bottom: 15px;">
                <i class="fas fa-camera" style="color: #4a7c2e;"></i>
                <strong>Image Analysis Complete:</strong> Your hair type was identified as <strong>${data.hair_type || 'Unknown'}</strong> 
                (${data.confidence ? (data.confidence * 100).toFixed(0) + '% confidence' : ''})
                ${data.conditions ? `• Conditions: ${data.conditions.join(', ')}` : ''}
            </div>
        `;
        resultsSection.insertBefore(modeInfo, resultsSection.firstChild);
    } else {
        modeInfo.innerHTML = `
            <div style="background: #f0f4ff; padding: 10px 15px; border-radius: 8px; margin-bottom: 15px;">
                <i class="fas fa-clipboard-list" style="color: #4a7c2e;"></i>
                <strong>Condition-Based Analysis:</strong> ${data.conditions ? `Conditions: ${data.conditions.join(', ')}` : ''}
                ${data.total_found ? `• Found ${data.total_found} herbs` : ''}
            </div>
        `;
        resultsSection.insertBefore(modeInfo, resultsSection.firstChild);
    }
    
    // Display summary
    const summaryContent = document.getElementById('summaryContent');
    if (summaryContent) {
        summaryContent.innerHTML = data.summary ? 
            data.summary.replace(/\n/g, '<br>') : 
            `Based on your ${data.hair_type ? data.hair_type + ' hair and ' : ''}conditions (${data.conditions.join(', ')}), we found ${data.total_found} herbs for you.`;
    }
    
    // Display recommendations
    const container = document.getElementById('recommendationsList');
    if (!container) return;
    
    if (!data.recommendations || data.recommendations.length === 0) {
        container.innerHTML = '<p style="color: #718096;">No herbs found for these conditions.</p>';
        return;
    }
    
    let html = '';
    data.recommendations.forEach((herb, index) => {
        // Get values with fallbacks
        const name = herb.herb_name || herb.name || 'Unknown Herb';
        const botanical = herb.botanical_name || '-';
        const sanskrit = herb.sanskrit_name || '-';
        const benefits = herb.benefits || 'Supports hair health';
        const howToUse = herb.how_to_use || 'Apply as directed';
        const hairTypes = herb.hair_types || 'All';
        const conditions = herb.conditions || 'Hair Growth';
        const matchScore = herb.match_score || herb.match_percentage || 0;
        const explanation = herb.ai_explanation || 'Traditional Ayurvedic recommendation.';
        const hairTypeMatch = herb.hair_type_match ? '✅ Matches your hair type' : '';
        
        const matchInfo = herb.matching_conditions && herb.matching_conditions.length > 0 
            ? `<span class="match-badge">✅ Matches: ${herb.matching_conditions.join(', ')}</span>`
            : '';
        
        const scoreHtml = matchScore > 0 
            ? `<span class="score-badge">Score: ${matchScore}</span>`
            : '';
        
        html += `
            <div class="recommendation-item">
                <h3>${index + 1}. ${name} ${matchInfo} ${scoreHtml}</h3>
                ${hairTypeMatch ? `<div class="benefit" style="color: #4a7c2e;"><i class="fas fa-check-circle"></i> ${hairTypeMatch}</div>` : ''}
                <div class="benefit">
                    <strong>Botanical:</strong> ${botanical}
                </div>
                <div class="benefit">
                    <strong>Sanskrit:</strong> ${sanskrit}
                </div>
                <div class="benefit">
                    <strong>Benefits:</strong> ${benefits}
                </div>
                <div class="benefit">
                    <strong>How to use:</strong> ${howToUse}
                </div>
                <div class="benefit">
                    <strong>Suitable for:</strong> ${hairTypes}
                </div>
                <div class="benefit">
                    <strong>Conditions:</strong> ${conditions}
                </div>
                <div class="explanation">
                    <strong>💡 Why this works:</strong><br>
                    ${explanation}
                </div>
                ${herb.active_compounds ? `<div class="benefit"><strong>Active compounds:</strong> ${herb.active_compounds}</div>` : ''}
                ${herb.evidence_level ? `<div class="benefit"><strong>Evidence level:</strong> ${herb.evidence_level}</div>` : ''}
            </div>
        `;
    });
    
    container.innerHTML = html;
    
    // Quick reference
    const quickRef = document.getElementById('quickReference');
    if (quickRef) {
        const herbNames = data.recommendations.slice(0, 5).map(h => h.herb_name || h.name).join(', ');
        quickRef.innerHTML = `
            <p><strong>Top ${Math.min(5, data.recommendations.length)} herbs for you:</strong></p>
            <p style="font-size: 18px; color: #2d5016;">${herbNames}</p>
            <p style="color: #718096; margin-top: 10px;">
                ${data.total_found > 5 ? `Plus ${data.total_found - 5} more herbs...` : ''}
                ${detailed ? '(Detailed analysis complete)' : '(Click "Detailed Analysis" for more info)'}
            </p>
            ${data.hair_type ? `<p style="color: #4a7c2e; margin-top: 10px;"><i class="fas fa-camera"></i> Analysis based on ${data.hair_type} hair type</p>` : ''}
        `;
    }
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

//  Load Knowledge Base 

async function loadKnowledgeBase() {
    try {
        const response = await fetch('/api/herbs');
        const data = await response.json();
        
        if (data.success && data.herbs) {
            populateTable(data.herbs);
        }
    } catch (error) {
        console.error('Error loading knowledge base:', error);
    }
}

function populateTable(herbs) {
    const tbody = document.getElementById('herbTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (!herbs || herbs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 40px; color: #718096;">No herbs found in the database.</td></tr>';
        return;
    }
    
    herbs.forEach(herb => {
        const row = document.createElement('tr');
        const name = herb.herb_name || herb.name || 'Unknown';
        const botanical = herb.botanical_name || '-';
        const sanskrit = herb.sanskrit_name || '-';
        const benefits = herb.benefits || 'N/A';
        const howToUse = herb.how_to_use || 'N/A';
        const hairTypes = herb.hair_types || 'All';
        const conditions = herb.conditions || 'General';
        
        row.innerHTML = `
            <td><strong>${name}</strong></td>
            <td><em>${botanical}</em></td>
            <td>${sanskrit}</td>
            <td style="max-width: 300px;">${benefits}</td>
            <td style="max-width: 200px;">${howToUse}</td>
            <td>${hairTypes}</td>
            <td>${conditions}</td>
        `;
        tbody.appendChild(row);
    });
}

//  Search Herbs 

async function searchHerbs() {
    const searchInput = document.getElementById('herbSearch');
    if (!searchInput) return;
    
    const query = searchInput.value.trim();
    if (!query) {
        loadKnowledgeBase();
        return;
    }
    
    try {
        const response = await fetch(`/api/herbs/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.success && data.results) {
            populateTable(data.results);
        }
    } catch (error) {
        console.error('Error searching herbs:', error);
    }
}

//  Event Listeners 

if (getBtn) getBtn.addEventListener('click', () => getRecommendations(false));
if (getDetailedBtn) getDetailedBtn.addEventListener('click', () => getRecommendations(true));

const searchBtn = document.getElementById('searchBtn');
const herbSearch = document.getElementById('herbSearch');

if (searchBtn) searchBtn.addEventListener('click', searchHerbs);
if (herbSearch) {
    herbSearch.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchHerbs();
    });
}

//  Initialise 

document.addEventListener('DOMContentLoaded', () => {
    loadConditions();
    loadKnowledgeBase();
});

// Check health
async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        console.log('✅ API Health:', data);
        console.log('📊 Mode:', data.mode);
        if (data.components && data.components.herb_database) {
            console.log(`📚 Herbs in database: ${data.components.herb_database.count}`);
        }
        if (data.components && data.components.hair_classifier) {
            console.log(`🧠 Classifier: ${data.components.hair_classifier.available ? 'Available' : 'Not available'}`);
        }
    } catch (error) {
        console.error('❌ Health check failed:', error);
    }
}

checkHealth();