;; process-org.el
(require 'org)

(org-babel-do-load-languages
 'org-babel-load-languages
 '((dot . t))) ;; Enable dot

(setq org-confirm-babel-evaluate nil) ;; No confirm prompt

(find-file "informe.org") ;; Your org file here
(org-babel-execute-buffer) ;; Run all src blocks
(save-buffer) ;; Save after execution
(kill-emacs)
