function previewDocument(archivo, extension) {
    const modal = new bootstrap.Modal(document.getElementById('previewModal'));
    const content = document.getElementById('previewContent');
    content.innerHTML = `
        <div class="d-flex justify-content-center align-items-center" style="height:400px;">
            <div class="spinner-border text-primary" role="status"><span class="visually-hidden">Cargando...</span></div>
        </div>
    `;

    fetch(`/uploads/${archivo}`, { method: 'HEAD' })
        .then(res => {
            if (!res.ok) throw new Error('Archivo no encontrado');

            const viewer = {
                pdf: () => `<iframe src="/uploads/${archivo}" width="100%" height="600px" style="border:none; background:#f8f9fa;"></iframe>`,
                office: () => {
                    const url = encodeURIComponent(window.location.origin + '/uploads/' + archivo);
                    return `
                        <iframe src="https://view.officeapps.live.com/op/embed.aspx?src=${url}" width="100%" height="600px" frameborder="0"></iframe>
                        <div class='text-center text-muted mt-2'>Si no se muestra correctamente, <a href='/download/${archivo}' target='_blank'>descarga el archivo</a>.</div>
                    `;
                },
                txt: () => fetch(`/uploads/${archivo}`)
                    .then(res => res.text())
                    .then(text => {
                        content.innerHTML = `<pre class='text-break bg-light p-3' style='white-space: pre-wrap;'>${text}</pre>`;
                    })
                    .catch(err => showError('Error al cargar el archivo de texto.', err.message))
            };

            if (extension === 'pdf') {
                content.innerHTML = viewer.pdf();
            } else if (["doc", "docx", "xls", "xlsx", "ppt", "pptx"].includes(extension)) {
                content.innerHTML = viewer.office();
            } else if (extension === 'txt') {
                viewer.txt();
            } else {
                showError('Formato de archivo no soportado para vista previa.');
            }
        })
        .catch(err => showError('Error al cargar el documento.', err.message));

    function showError(title, message = '') {
        content.innerHTML = `
            <div class='text-center text-danger'>
                <strong>${title}</strong><br>
                <span>${message}</span><br>
                <a href='/download/${archivo}' class='btn btn-outline-primary mt-2'>Intentar descargar</a>
            </div>
        `;
    }

    modal.show();
}


function shareDocument(archivo) {
    const url = `${window.location.origin}/uploads/${archivo}`;
    const content = document.getElementById('shareContent');

    content.innerHTML = `
        <div class="mb-3">
            <label class="form-label fw-semibold">Enlace directo:</label>
            <div class="input-group">
                <input type="text" class="form-control" value="${url}" readonly id="shareLinkInput">
                <button class="btn btn-outline-primary" onclick="navigator.clipboard.writeText('${url}')">
                    <i class="fas fa-copy me-1"></i> Copiar
                </button>
            </div>
        </div>

        <div class="mb-3">
            <label class="form-label fw-semibold">Compartir vía:</label>
            <div class="d-flex flex-wrap gap-2">
                <a href="mailto:?subject=Documento compartido&body=${encodeURIComponent(url)}"
                   class="btn btn-outline-secondary btn-sm"><i class="fas fa-envelope me-1"></i> Outlook</a>
                <a href="https://teams.microsoft.com/l/message/19:general?body=${encodeURIComponent(url)}"
                   target="_blank" class="btn btn-outline-secondary btn-sm"><i class="fab fa-microsoft me-1"></i> Teams</a>
                <a href="https://web.whatsapp.com/send?text=${encodeURIComponent(url)}"
                   target="_blank" class="btn btn-outline-secondary btn-sm"><i class="fab fa-whatsapp me-1"></i> WhatsApp</a>
                <a href="https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}"
                   target="_blank" class="btn btn-outline-secondary btn-sm"><i class="fab fa-linkedin me-1"></i> LinkedIn</a>
            </div>
        </div>
    `;

    const modal = new bootstrap.Modal(document.getElementById('shareModal'));
    modal.show();
}

// Función para eliminar backdrop residual
function removeBackdrop() {
    document.querySelectorAll('.modal-backdrop').forEach(function (el) {
        el.parentNode.removeChild(el);
    });
    document.body.classList.remove('modal-open');
    document.body.style.overflow = 'auto';
}

// Asegurar que los modales no bloqueen la pantalla
function setupModalListeners() {
    document.addEventListener('hidden.bs.modal', function () {
        removeBackdrop();
    });

    document.addEventListener('shown.bs.modal', function () {
        removeBackdrop();
    });
}

// Llamar a la configuración de listeners al cargar el script
setupModalListeners();
