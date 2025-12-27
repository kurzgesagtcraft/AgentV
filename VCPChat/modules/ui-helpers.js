// modules/ui-helpers.js
(function() {
    'use strict';

    // --- State for helper functions ---
    let croppedAgentAvatarFile = null;
    let croppedUserAvatarFile = null;
    let croppedGroupAvatarFile = null;

    const uiHelperFunctions = {};

    /**
     * 从字符串中解析正则表达式（支持 /pattern/flags 格式）
     * @param {string} input - 正则表达式字符串，如 "/test/gi" 或普通字符串 "test"
     * @returns {RegExp|null} - 返回RegExp对象，如果解析失败则返回null
     */
    uiHelperFunctions.regexFromString = function(input) {
        if (!input || typeof input !== 'string') {
            return null;
        }
        
        // 终极修复：废除使用正则表达式解析正则表达式的脆弱方法。
        // 改为使用明确的、手动字符串分割，这能从根本上避免转义地狱。
        if (input.length < 2 || !input.startsWith('/') || input.lastIndexOf('/') === 0) {
            console.error(`[regexFromString] 无效的格式: "${input}"。规则必须采用 /pattern/flags 的格式。`);
            return null;
        }

        try {
            const lastSlashIndex = input.lastIndexOf('/');
            const pattern = input.substring(1, lastSlashIndex);
            const flags = input.substring(lastSlashIndex + 1);
            
            // 这是最稳定、最可靠的创建方式
            return new RegExp(pattern, flags);
            
        } catch (e) {
            console.error(`[regexFromString] 解析正则表达式 "${input}" 失败:`, e);
            return null;
        }
    };

    /**
     * Scrolls the chat messages div to the bottom.
     */
    uiHelperFunctions.scrollToBottom = function() {
        const chatMessagesDiv = document.getElementById('chatMessages');
        if (!chatMessagesDiv) return;

        // 关键修正：滚动检查必须在调用时进行，而不是在动画帧回调中。
        // 这确保我们基于当前的用户滚动位置来决定是否要滚动。
        const scrollThreshold = 20; // 像素容差
        const isScrolledToBottom = chatMessagesDiv.scrollHeight - chatMessagesDiv.clientHeight <= chatMessagesDiv.scrollTop + scrollThreshold;

        // 只有当用户已经位于底部时，才执行自动滚动。
        if (isScrolledToBottom) {
            // 使用 requestAnimationFrame 来确保滚动操作在下一次浏览器重绘前执行。
            // 这可以保证在执行滚动时，DOM的布局和尺寸计算已经完成，从而获取到最准确的 scrollHeight 值。
            requestAnimationFrame(() => {
                // 在动画帧回调中再次检查元素是否存在，以防万一。
                if (document.body.contains(chatMessagesDiv)) {
                    chatMessagesDiv.scrollTop = chatMessagesDiv.scrollHeight;
                    const parentContainer = document.querySelector('.chat-messages-container');
                    if (parentContainer) {
                        parentContainer.scrollTop = parentContainer.scrollHeight;
                    }
                }
            });
        }
    };

    /**
     * Automatically resizes a textarea to fit its content.
     * @param {HTMLTextAreaElement} textarea The textarea element.
     */
    uiHelperFunctions.autoResizeTextarea = function(textarea) {
        if (!textarea) return;
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
    };

    /**
     * Opens a modal dialog by its ID.
     * @param {string} modalId The ID of the modal element.
     */
    uiHelperFunctions.openModal = function(modalId) {
        const modalElement = document.getElementById(modalId);
        if (modalElement) modalElement.classList.add('active');
    };

    /**
     * Closes a modal dialog by its ID.
     * @param {string} modalId The ID of the modal element.
     */
    uiHelperFunctions.closeModal = function(modalId) {
        const modalElement = document.getElementById(modalId);
        if (modalElement) modalElement.classList.remove('active');
    };

    /**
     * Shows a toast notification.
     * @param {string} message The message to display.
     * @param {number} [duration=3000] The duration in milliseconds.
     */
    uiHelperFunctions.showToastNotification = function(message, type = 'info', duration = 3000) {
        const container = document.getElementById('floating-toast-notifications-container');
        if (!container) {
            console.warn("Toast notification container not found.");
            alert(message); // Fallback
            return;
        }

        const toast = document.createElement('div');
        toast.className = `floating-toast-notification ${type}`; // e.g., 'info', 'success', 'error'
        toast.textContent = message;

        container.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.classList.add('visible');
        });

        const removeToast = () => {
            if (!toast.parentNode) return; // Already removed
            toast.classList.remove('visible');
            toast.classList.add('exiting');
            
            const onTransitionEnd = (event) => {
                if (event.propertyName === 'transform' && toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                    toast.removeEventListener('transitionend', onTransitionEnd);
                }
            };
            toast.addEventListener('transitionend', onTransitionEnd);

            // Fallback removal
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 500); // Should match animation duration
        };

        // Set timer to animate out and remove
        const removalTimeout = setTimeout(removeToast, duration);

        // Add click listener to remove early
        toast.addEventListener('click', () => {
            clearTimeout(removalTimeout); // Cancel the scheduled removal
            removeToast();
        });
    };

    /**
     * Shows temporary feedback on a button after an action.
     * @param {HTMLButtonElement} buttonElement The button element.
     * @param {boolean} success Whether the action was successful.
     * @param {string} tempText The temporary text to show.
     * @param {string} originalText The original text of the button.
     */
    uiHelperFunctions.showSaveFeedback = function(buttonElement, success, tempText, originalText) {
        if (!buttonElement) return;
        buttonElement.textContent = tempText;
        buttonElement.disabled = true;
        if (!success) buttonElement.classList.add('error-feedback');

        setTimeout(() => {
            buttonElement.textContent = originalText;
            buttonElement.disabled = false;
            if (!success) buttonElement.classList.remove('error-feedback');
        }, success ? 2000 : 3000);
    };

    /**
     * Shows a topic context menu (delegated to topicListManager).
     * @param {Event} event The context menu event.
     * @param {HTMLElement} topicItemElement The topic list item element.
     * @param {Object} itemFullConfig The full item configuration.
     * @param {Object} topic The topic object.
     * @param {string} itemType The item type ('agent' or 'group').
     */
    uiHelperFunctions.showTopicContextMenu = function(event, topicItemElement, itemFullConfig, topic, itemType) {
        // Delegate to topicListManager if available
        if (window.topicListManager && window.topicListManager.showTopicContextMenu) {
            window.topicListManager.showTopicContextMenu(event, topicItemElement, itemFullConfig, topic, itemType);
        } else {
            console.warn('[UI Helper] topicListManager.showTopicContextMenu not available');
        }
    };

    /**
     * Opens an avatar cropping modal.
     * @param {File} file The image file to crop.
     * @param {function(File): void} onCropConfirmedCallback Callback with the cropped file.
     * @param {string} [cropType='agent'] The type of avatar ('agent', 'group', 'user').
     */
    uiHelperFunctions.openAvatarCropper = async function(file, onCropConfirmedCallback, cropType = 'agent') {
        const cropperContainer = document.getElementById('avatarCropperContainer');
        const canvas = document.getElementById('avatarCanvas');
        const confirmCropBtn = document.getElementById('confirmCropBtn');
        const cancelCropBtn = document.getElementById('cancelCropBtn');

        if (!cropperContainer || !canvas || !confirmCropBtn || !cancelCropBtn) {
            console.error("Avatar cropper elements not found!");
            return;
        }
        
        const ctx = canvas.getContext('2d');
        const cropCircleSVG = document.getElementById('cropCircle');
        const cropCircleBorderSVG = document.getElementById('cropCircleBorder');

        uiHelperFunctions.openModal('avatarCropperModal');
        canvas.style.display = 'block';
        cropperContainer.style.cursor = 'grab';

        let img = new Image();
        let currentEventListeners = {};

        img.onload = () => {
            canvas.width = 360;
            canvas.height = 360;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = 'rgba(255, 255, 255, 0)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            let scale = Math.min(canvas.width / img.width, canvas.height / img.height);
            let scaledWidth = img.width * scale;
            let scaledHeight = img.height * scale;
            let offsetX = (canvas.width - scaledWidth) / 2;
            let offsetY = (canvas.height - scaledHeight) / 2;
            ctx.drawImage(img, offsetX, offsetY, scaledWidth, scaledHeight);

            let circle = { x: canvas.width / 2, y: canvas.height / 2, r: Math.min(canvas.width / 2, canvas.height / 2, 100) };
            updateCircleSVG();

            let isDragging = false;
            let dragStartX, dragStartY, circleStartX, circleStartY;

            function updateCircleSVG() {
                cropCircleSVG.setAttribute('cx', circle.x);
                cropCircleSVG.setAttribute('cy', circle.y);
                cropCircleSVG.setAttribute('r', circle.r);
                cropCircleBorderSVG.setAttribute('cx', circle.x);
                cropCircleBorderSVG.setAttribute('cy', circle.y);
                cropCircleBorderSVG.setAttribute('r', circle.r);
            }

            currentEventListeners.onMouseDown = (e) => {
                const rect = cropperContainer.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;
                if (Math.sqrt((mouseX - circle.x)**2 + (mouseY - circle.y)**2) < circle.r + 10) {
                    isDragging = true;
                    dragStartX = mouseX;
                    dragStartY = mouseY;
                    circleStartX = circle.x;
                    circleStartY = circle.y;
                    cropperContainer.style.cursor = 'grabbing';
                }
            };

            currentEventListeners.onMouseMove = (e) => {
                if (!isDragging) return;
                const rect = cropperContainer.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;
                circle.x = circleStartX + (mouseX - dragStartX);
                circle.y = circleStartY + (mouseY - dragStartY);
                circle.x = Math.max(circle.r, Math.min(canvas.width - circle.r, circle.x));
                circle.y = Math.max(circle.r, Math.min(canvas.height - circle.r, circle.y));
                updateCircleSVG();
            };

            currentEventListeners.onMouseUpOrLeave = () => {
                isDragging = false;
                cropperContainer.style.cursor = 'grab';
            };

            currentEventListeners.onWheel = (e) => {
                e.preventDefault();
                const zoomFactor = e.deltaY < 0 ? 1.05 : 0.95;
                const newRadius = Math.max(30, Math.min(Math.min(canvas.width, canvas.height) / 2, circle.r * zoomFactor));
                if (newRadius === circle.r) return;
                circle.r = newRadius;
                circle.x = Math.max(circle.r, Math.min(canvas.width - circle.r, circle.x));
                circle.y = Math.max(circle.r, Math.min(canvas.height - circle.r, circle.y));
                updateCircleSVG();
            };

            currentEventListeners.onConfirmCrop = () => {
                const finalCropCanvas = document.createElement('canvas');
                const finalSize = circle.r * 2;
                finalCropCanvas.width = finalSize;
                finalCropCanvas.height = finalSize;
                const finalCtx = finalCropCanvas.getContext('2d');

                finalCtx.drawImage(canvas,
                    circle.x - circle.r, circle.y - circle.r,
                    finalSize, finalSize,
                    0, 0,
                    finalSize, finalSize
                );

                finalCtx.globalCompositeOperation = 'destination-in';
                finalCtx.beginPath();
                finalCtx.arc(circle.r, circle.r, circle.r, 0, Math.PI * 2);
                finalCtx.fill();
                finalCtx.globalCompositeOperation = 'source-over';

                finalCropCanvas.toBlob((blob) => {
                    if (!blob) {
                        console.error("[AvatarCropper] Failed to create blob from final canvas.");
                        uiHelperFunctions.showToastNotification("裁剪失败，无法生成图片数据。", 'error');
                        return;
                    }
                    const croppedFile = new File([blob], `${cropType}_avatar.png`, { type: "image/png" });
                    if (typeof onCropConfirmedCallback === 'function') {
                        onCropConfirmedCallback(croppedFile);
                    }
                    cleanupAndClose();
                }, 'image/png');
            };

            currentEventListeners.onCancelCrop = () => {
                cleanupAndClose();
                const agentAvatarInput = document.getElementById('agentAvatarInput');
                const userAvatarInput = document.getElementById('userAvatarInput');
                if (cropType === 'agent' && agentAvatarInput) agentAvatarInput.value = '';
                else if (cropType === 'user' && userAvatarInput) userAvatarInput.value = '';
                else if (cropType === 'group' && window.GroupRenderer) {
                    const groupAvatarInputElement = document.getElementById('groupAvatarInput');
                    if (groupAvatarInputElement) groupAvatarInputElement.value = '';
                }
            };

            function cleanupAndClose() {
                cropperContainer.removeEventListener('mousedown', currentEventListeners.onMouseDown);
                document.removeEventListener('mousemove', currentEventListeners.onMouseMove);
                document.removeEventListener('mouseup', currentEventListeners.onMouseUpOrLeave);
                cropperContainer.removeEventListener('mouseleave', currentEventListeners.onMouseUpOrLeave);
                cropperContainer.removeEventListener('wheel', currentEventListeners.onWheel);
                confirmCropBtn.removeEventListener('click', currentEventListeners.onConfirmCrop);
                cancelCropBtn.removeEventListener('click', currentEventListeners.onCancelCrop);
                uiHelperFunctions.closeModal('avatarCropperModal');
            }

            cropperContainer.addEventListener('mousedown', currentEventListeners.onMouseDown);
            document.addEventListener('mousemove', currentEventListeners.onMouseMove);
            document.addEventListener('mouseup', currentEventListeners.onMouseUpOrLeave);
            cropperContainer.addEventListener('mouseleave', currentEventListeners.onMouseUpOrLeave);
            cropperContainer.addEventListener('wheel', currentEventListeners.onWheel);
            confirmCropBtn.addEventListener('click', currentEventListeners.onConfirmCrop);
            cancelCropBtn.addEventListener('click', currentEventListeners.onCancelCrop);
        };

        img.onerror = () => {
            console.error("[AvatarCropper] Image failed to load from blob URL.");
            uiHelperFunctions.showToastNotification("无法加载选择的图片，请尝试其他图片。", 'error');
            uiHelperFunctions.closeModal('avatarCropperModal');
        };
        img.src = URL.createObjectURL(file);
    };

    /**
     * Updates the attachment preview area with current attached files.
     * @param {Array} attachedFiles Array of attached file objects.
     * @param {HTMLElement} attachmentPreviewArea The preview area element.
     */
    uiHelperFunctions.updateAttachmentPreview = function(attachedFiles, attachmentPreviewArea) {
        if (!attachmentPreviewArea) {
            console.error('[UI Helper] updateAttachmentPreview: attachmentPreviewArea is null or undefined!');
            return;
        }
    
        attachmentPreviewArea.innerHTML = ''; // Clear previous previews
        if (attachedFiles.length === 0) {
            attachmentPreviewArea.style.display = 'none';
            return;
        }
        attachmentPreviewArea.style.display = 'flex'; // Show the area
    
        attachedFiles.forEach((af, index) => {
            const prevDiv = document.createElement('div');
            prevDiv.className = 'attachment-preview-item';
            prevDiv.title = af.originalName || af.file.name;
    
            const fileType = af.file.type;
    
            if (fileType.startsWith('image/')) {
                const thumbnailImg = document.createElement('img');
                thumbnailImg.className = 'attachment-thumbnail-image';
                thumbnailImg.src = af.localPath; // Assumes localPath is a usable URL (e.g., file://)
                thumbnailImg.alt = af.originalName || af.file.name;
                thumbnailImg.onerror = () => { // Fallback to icon if image fails to load
                    thumbnailImg.remove(); // Remove broken image
                    const iconSpanFallback = document.createElement('span');
                    iconSpanFallback.className = 'file-preview-icon';
                    iconSpanFallback.textContent = '⚠️'; // Error/fallback icon
                    prevDiv.prepend(iconSpanFallback); // Add fallback icon at the beginning
                };
                prevDiv.appendChild(thumbnailImg);
            } else {
                const iconSpan = document.createElement('span');
                iconSpan.className = 'file-preview-icon';
                if (fileType.startsWith('audio/')) {
                    iconSpan.textContent = '🎵';
                } else if (fileType.startsWith('video/')) {
                    iconSpan.textContent = '🎞️';
                } else if (fileType.includes('pdf')) {
                    iconSpan.textContent = '📄';
                } else {
                    iconSpan.textContent = '📎';
                }
                prevDiv.appendChild(iconSpan);
            }
    
            const nameSpan = document.createElement('span');
            nameSpan.className = 'file-preview-name';
            const displayName = af.originalName || af.file.name;
            nameSpan.textContent = displayName.length > 20 ? displayName.substring(0, 17) + '...' : displayName;
            prevDiv.appendChild(nameSpan);
    
            const removeBtn = document.createElement('button');
            removeBtn.className = 'file-preview-remove-btn';
            removeBtn.innerHTML = '×';
            removeBtn.title = '移除此附件';
            removeBtn.onclick = () => {
                attachedFiles.splice(index, 1);
                uiHelperFunctions.updateAttachmentPreview(attachedFiles, attachmentPreviewArea);
            };
            prevDiv.appendChild(removeBtn);
    
            attachmentPreviewArea.appendChild(prevDiv);
        });
    };

    /**
     * Helper to get a centrally stored cropped file (agent, group, or user).
     * @param {string} type The type of avatar ('agent', 'group', 'user').
     * @returns {File|null} The cropped file or null.
     */
    uiHelperFunctions.getCroppedFile = function(type) {
        if (type === 'agent') return croppedAgentAvatarFile;
        if (type === 'group') return croppedGroupAvatarFile;
        if (type === 'user') return croppedUserAvatarFile;
        return null;
    };

    /**
     * Helper to set a centrally stored cropped file.
     * @param {string} type The type of avatar ('agent', 'group', 'user').
     * @param {File|null} file The cropped file to store.
     */
    uiHelperFunctions.setCroppedFile = function(type, file) {
        if (type === 'agent') croppedAgentAvatarFile = file;
        else if (type === 'group') croppedGroupAvatarFile = file;
        else if (type === 'user') croppedUserAvatarFile = file;
    };

    /**
     * Function to extract average color from an avatar image.
     * @param {string} imageUrl The URL of the image.
     * @param {function(string): void} callback Callback with the average color.
     */
    uiHelperFunctions.getAverageColorFromAvatar = function(imageUrl, callback) {
        const img = new Image();
        img.crossOrigin = "Anonymous";
        img.onload = function() {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);

            try {
                const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                const data = imageData.data;
                let r = 0, g = 0, b = 0, count = 0;

                for (let i = 0; i < data.length; i += 4) {
                    if (data[i + 3] > 0) { // Only count non-transparent pixels
                        r += data[i];
                        g += data[i + 1];
                        b += data[i + 2];
                        count++;
                    }
                }

                if (count > 0) {
                    r = Math.round(r / count);
                    g = Math.round(g / count);
                    b = Math.round(b / count);
                    const avgColor = `rgb(${r}, ${g}, ${b})`;
                    callback(avgColor);
                } else {
                    callback(null);
                }
            } catch (error) {
                console.error('[UI Helper] Error extracting color from avatar:', error);
                callback(null);
            }
        };
        img.onerror = function() {
            console.error('[UI Helper] Failed to load image for color extraction:', imageUrl);
            callback(null);
        };
        img.src = imageUrl;
    };

    uiHelperFunctions.prepareGroupSettingsDOM = function() {
        // This function is called early in DOMContentLoaded.
        // It ensures the container for group settings exists.
        // The actual content (form fields) will be managed by GroupRenderer.
        if (!document.getElementById('groupSettingsContainer')) {
            const settingsTab = document.getElementById('tabContentSettings');
            if (settingsTab) {
                const groupContainerHTML = `<div id="groupSettingsContainer" style="display: none;"></div>`;
                settingsTab.insertAdjacentHTML('beforeend', groupContainerHTML);
                console.log("[UI Helper] groupSettingsContainer placeholder created.");
            } else {
                console.error("[UI Helper] Could not find tabContentSettings to append group settings DOM placeholder.");
            }
        }
         // Ensure createNewGroupBtn has its text updated
         const createNewAgentBtn = document.getElementById('createNewAgentBtn');
         const createNewGroupBtn = document.getElementById('createNewGroupBtn');
         if (createNewAgentBtn) {
             createNewAgentBtn.textContent = '创建 Agent';
         }
         if (createNewGroupBtn) {
             createNewGroupBtn.textContent = '创建 Group';
             console.log('[UI Helper prepareGroupSettingsDOM] createNewGroupBtn textContent set to:', createNewGroupBtn.textContent);
             createNewGroupBtn.style.display = 'inline-block'; // Make it visible
         }
    };

    uiHelperFunctions.addNetworkPathInput = function(path = '') {
        const container = document.getElementById('networkNotesPathsContainer');
        const inputGroup = document.createElement('div');
        inputGroup.className = 'network-path-input-group';
    
        const input = document.createElement('input');
        input.type = 'text';
        input.name = 'networkNotesPath';
        input.placeholder = '例如 \\\\NAS\\Shared\\Notes';
        input.value = path;
        input.style.flexGrow = '1';
    
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.textContent = '删除';
        removeBtn.className = 'sidebar-button small-button danger-button'; // Re-use existing styles
        removeBtn.style.width = 'auto';
        removeBtn.onclick = () => {
            inputGroup.remove();
        };
    
        inputGroup.appendChild(input);
        inputGroup.appendChild(removeBtn);
        container.appendChild(inputGroup);
    };

    uiHelperFunctions.filterAgentList = function(searchTerm) {
        const lowerCaseSearchTerm = searchTerm.toLowerCase().trim();
        const itemListUl = document.getElementById('agentList'); // Renamed from agentListUl to itemListUl
        if (!itemListUl) return;
        const items = itemListUl.querySelectorAll('li'); // Get all list items
    
        items.forEach(item => {
            const nameElement = item.querySelector('.agent-name');
            if (nameElement) {
                const name = nameElement.textContent.toLowerCase();
                if (name.includes(lowerCaseSearchTerm)) {
                    item.style.display = ''; // Reset to default display style from CSS
                } else {
                    item.style.display = 'none';
                }
            }
        });
    };

    /**
     * Updates the speaking indicator animation on an avatar.
     * @param {string} msgId The ID of the message item.
     * @param {boolean} isSpeaking True to show the indicator, false to hide it.
     */
    uiHelperFunctions.updateSpeakingIndicator = function(msgId, isSpeaking) {
        const messageItem = document.querySelector(`.message-item[data-message-id="${msgId}"]`);
        if (messageItem) {
            const avatarElement = messageItem.querySelector('.chat-avatar');
            if (avatarElement) {
                if (isSpeaking) {
                    avatarElement.classList.add('speaking');
                } else {
                    avatarElement.classList.remove('speaking');
                }
            }
        }
    };

    window.uiHelperFunctions = uiHelperFunctions;

})();