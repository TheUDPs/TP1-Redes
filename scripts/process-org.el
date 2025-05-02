;; process-org.el
(require 'org)

(setq org-plantuml-exec-mode 'plantuml)

(org-babel-do-load-languages
 'org-babel-load-languages
 '((dot . t)        ;; Enable Graphviz DOT
   (plantuml . t))) ;; Enable PlantUML

(setq org-confirm-babel-evaluate nil) ;; No confirm prompt

(find-file "informe.org") ;; Your org file here
(org-babel-execute-buffer) ;; Run all src blocks
(save-buffer) ;; Save after execution
(kill-emacs)
