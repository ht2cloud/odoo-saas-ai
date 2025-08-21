odoo.define('odoo_ai_chat.AIChatWidget', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var rpc = require('web.rpc');

var QWeb = core.qweb;
var _t = core._t;

var AIChatWidget = AbstractAction.extend({
    template: 'ai_chat_widget_template',
    
    events: {
        'click .example-item': '_onExampleClick',
        'click #sendBtn': '_onGenerateClick',
        'keypress #promptInput': '_onKeyPress',
        'click .install-btn': '_onInstallClick',
    },
    
    init: function(parent, context) {
        this._super(parent, context);
        this.currentSessionId = null;
        this.pollInterval = null;
    },
    
    start: function() {
        var self = this;
        return this._super().then(function() {
            self._addWelcomeMessage();
        });
    },
    
    destroy: function() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
        this._super();
    },
    
    _onExampleClick: function(event) {
        var text = $(event.currentTarget).text();
        this.$('#promptInput').val(text);
    },
    
    _onKeyPress: function(event) {
        if (event.which === 13) { // Enter key
            this._onGenerateClick();
        }
    },
    
    _onGenerateClick: function() {
        var requirements = this.$('#promptInput').val().trim();
        if (!requirements) {
            return;
        }
        
        var $sendBtn = this.$('#sendBtn');
        $sendBtn.prop('disabled', true).text('Generating...');
        
        this._addMessage(requirements, 'user');
        this._showProgress();
        
        var self = this;
        rpc.query({
            route: '/ai_chat/generate',
            params: {
                requirements: requirements,
                options: {}
            }
        }).then(function(result) {
            if (result.error) {
                self._addMessage('❌ Error: ' + result.error, 'error');
                self._hideProgress();
                $sendBtn.prop('disabled', false).text('Generate');
            } else {
                self.currentSessionId = result.session_id;
                self._addMessage('🚀 Generation started...', 'system');
                self._startPolling();
            }
        }).catch(function(error) {
            self._addMessage('❌ Network error occurred', 'error');
            self._hideProgress();
            $sendBtn.prop('disabled', false).text('Generate');
        });
    },
    
    _onInstallClick: function(event) {
        var sessionId = $(event.currentTarget).data('session-id');
        if (!sessionId) {
            return;
        }
        
        var $btn = $(event.currentTarget);
        $btn.prop('disabled', true).text('Installing...');
        
        var self = this;
        rpc.query({
            route: '/ai_chat/install/' + sessionId,
            params: {}
        }).then(function(result) {
            if (result.error) {
                self._addMessage('❌ Installation failed: ' + result.error, 'error');
            } else if (result.success) {
                self._addMessage('✅ Module "' + result.module_name + '" installed successfully!', 'success');
                // Optionally reload the page to show the new module
                if (confirm('Module installed successfully! Would you like to reload to see the changes?')) {
                    window.location.reload();
                }
            } else {
                self._addMessage('❌ Installation failed: ' + result.message, 'error');
            }
            $btn.prop('disabled', false).text('Install Module');
        }).catch(function(error) {
            self._addMessage('❌ Installation error occurred', 'error');
            $btn.prop('disabled', false).text('Install Module');
        });
    },
    
    _startPolling: function() {
        var self = this;
        this.pollInterval = setInterval(function() {
            if (self.currentSessionId) {
                self._checkStatus();
            }
        }, 2000);
    },
    
    _checkStatus: function() {
        var self = this;
        rpc.query({
            route: '/ai_chat/status/' + this.currentSessionId,
            params: {}
        }).then(function(data) {
            if (data.error) {
                self._addMessage('❌ Session error: ' + data.error, 'error');
                self._stopPolling();
                return;
            }
            
            self._updateProgress(data.progress || 0, self._getStatusMessage(data.status));
            
            if (data.status === 'completed' && data.result) {
                self._showResults(data.result);
                self._addMessage('✅ Module generated successfully!', 'success');
                self._stopPolling();
                self.$('#sendBtn').prop('disabled', false).text('Generate');
            } else if (data.status === 'failed') {
                self._addMessage('❌ Generation failed: ' + (data.error || 'Unknown error'), 'error');
                self._hideProgress();
                self._stopPolling();
                self.$('#sendBtn').prop('disabled', false).text('Generate');
            }
        }).catch(function(error) {
            console.error('Status check failed:', error);
        });
    },
    
    _stopPolling: function() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        this.currentSessionId = null;
    },
    
    _getStatusMessage: function(status) {
        var messages = {
            'pending': 'Initializing...',
            'parsing': 'Parsing requirements...',
            'generating': 'Generating code...',
            'analyzing': 'Analyzing security...',
            'completing': 'Finalizing module...',
            'completed': 'Complete!',
            'failed': 'Failed'
        };
        return messages[status] || 'Processing...';
    },
    
    _addMessage: function(content, type) {
        type = type || 'system';
        var $messages = this.$('#aiMessages');
        var $message = $('<div class="message ' + type + '">' + content + '</div>');
        $messages.append($message);
        $messages.scrollTop($messages[0].scrollHeight);
    },
    
    _addWelcomeMessage: function() {
        this._addMessage('👋 Welcome! Describe your Odoo module requirements in plain English, and I\'ll generate a complete, working module for you in real-time.');
    },
    
    _showProgress: function() {
        this.$('#progressSection').removeClass('hidden');
        this.$('#placeholderContent').addClass('hidden');
        this.$('#resultsContainer').addClass('hidden');
    },
    
    _hideProgress: function() {
        this.$('#progressSection').addClass('hidden');
        this.$('#placeholderContent').removeClass('hidden');
    },
    
    _updateProgress: function(progress, message) {
        this.$('#progressFill').css('width', progress + '%');
        this.$('#progressText').text(message);
    },
    
    _showResults: function(result) {
        this.$('#progressSection').addClass('hidden');
        this.$('#placeholderContent').addClass('hidden');
        
        var $container = this.$('#resultsContainer');
        $container.removeClass('hidden');
        
        var securityClass = this._getScoreClass(result.security_score);
        
        var html = `
            <div class="result-card">
                <h3>✅ Module Generated Successfully</h3>
                <div class="results-grid">
                    <div class="stat-card">
                        <div class="stat-number">${result.files_generated}</div>
                        <div class="stat-label">Files Generated</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${result.models_count}</div>
                        <div class="stat-label">Models Created</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${result.views_count}</div>
                        <div class="stat-label">Views Generated</div>
                    </div>
                    <div class="stat-card">
                        <div class="security-score ${securityClass}">${result.security_score.toFixed(1)}/100</div>
                        <div class="stat-label">Security Score</div>
                    </div>
                </div>
                
                <div class="module-info">
                    <h4>📦 ${result.module_name}</h4>
                    <p>${result.description}</p>
                </div>
                
                ${result.security_issues > 0 || result.compliance_issues > 0 ? `
                    <div class="security-info">
                        <h5>🔒 Security Analysis</h5>
                        <p>Security Issues: ${result.security_issues} | Compliance Issues: ${result.compliance_issues}</p>
                    </div>
                ` : ''}
                
                <div class="action-buttons">
                    <button class="btn btn-success install-btn" data-session-id="${this.currentSessionId}">
                        📥 Install Module
                    </button>
                </div>
            </div>
        `;
        
        $container.html(html);
    },
    
    _getScoreClass: function(score) {
        if (score >= 90) return 'score-excellent';
        if (score >= 75) return 'score-good';
        if (score >= 60) return 'score-warning';
        return 'score-danger';
    }
});

// Register the widget
core.action_registry.add('ai_chat_widget', AIChatWidget);

// Template for the widget
QWeb.add_template(`
<div t-name="ai_chat_widget_template" class="ai-chat-container">
    <div class="ai-chat-header">
        <h1>🤖 AI Module Generator</h1>
        <p>Transform your ideas into working Odoo modules instantly</p>
    </div>

    <div class="ai-chat-main-content">
        <div class="ai-chat-section">
            <div class="ai-chat-examples">
                <h4>💡 Try these examples:</h4>
                <div class="example-item">Customer management system with contact tracking</div>
                <div class="example-item">Sales dashboard with lead tracking and revenue reports</div>
                <div class="example-item">Inventory management with barcode scanning</div>
                <div class="example-item">Project management with task tracking and time logging</div>
            </div>

            <div class="ai-chat-container-inner">
                <div class="ai-messages" id="aiMessages">
                </div>

                <div class="ai-input-section">
                    <input type="text" class="ai-input-field" id="promptInput" 
                           placeholder="Describe your module requirements... (e.g., 'I need a customer management system with contact tracking')"/>
                    <button class="ai-send-btn" id="sendBtn">Generate</button>
                </div>
            </div>
        </div>

        <div class="ai-results-section">
            <div id="progressSection" class="hidden">
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill"></div>
                    </div>
                    <div class="progress-text" id="progressText">Initializing...</div>
                </div>
            </div>

            <div id="resultsContainer" class="hidden">
                <!-- Results will be populated here -->
            </div>

            <div id="placeholderContent">
                <div class="result-card">
                    <h3>🚀 Ready to Generate</h3>
                    <p>Enter your module requirements on the left to see:</p>
                    <ul style="margin-top: 15px; padding-left: 20px;">
                        <li>Real-time progress updates</li>
                        <li>Generated module statistics</li>
                        <li>Security analysis results</li>
                        <li>Direct module installation</li>
                        <li>Module management tools</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
</div>
`);

return AIChatWidget;

});