;; export-to-pdf.el - Export Org file to PDF and always save LaTeX output

;; Check if a filename is provided
(when (< (length command-line-args-left) 1)
  (error "Usage: emacs --batch -Q --script export-to-pdf.el <file.org>"))

;; Load required libraries
(require 'org)
(require 'ox-latex)

;; Configure paths
(setq org-file (car command-line-args-left))
(setq log-file (concat (file-name-sans-extension org-file) ".pdf.log"))

;; Open the Org file
(find-file org-file)

;; Perform export and handle output
(let ((export-success nil)
      (error-buffer nil))
  ;; Attempt PDF export
  (setq export-success (org-latex-export-to-pdf))

  ;; Always capture the LaTeX output buffer
  (setq error-buffer (get-buffer "*Org PDF LaTeX Output*"))

  (when error-buffer
  ;; Write buffer contents to log file
  (with-current-buffer error-buffer
    (setq coding-system-for-write 'utf-8) ;; Avoid prompt
    (write-region (point-min) (point-max) log-file))
  (message "LaTeX output saved to: %s" log-file))

  ;; Exit with appropriate status
  (if export-success
      (kill-emacs 0)
    (kill-emacs 1)))
