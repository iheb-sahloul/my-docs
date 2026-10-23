# Leadership & Comportemental (STAR)

> Leadership technique : feedback, conflits, parties prenantes, estimation, santé d'équipe. Les questions d'architecture sont dans [System Design](system-design.md). Les questions comportementales (« Parlez-moi d'une fois où… ») sont dans la [section Comportemental](#behavioral-star).
>
> **Note :** les chiffres des réponses STAR (pourcentages, délais, tailles d'équipe) sont illustratifs. Remplacez-les par vos propres chiffres réels avant d'utiliser une histoire.

## 🟢 Fondamentaux

### Leadership

#### Q1. Qu'est-ce qui rend le feedback technique et le mentorat réellement efficaces, et pas seulement corrects ? {#technical-feedback-mentorship-effective-opposed}
Un feedback efficace est spécifique (il pointe la ligne/la décision réelle, pas une impression générale),
opportun (donné près du moment où le travail a été fait, pas regroupé dans un vague commentaire trimestriel),
centré sur le travail et son impact plutôt que sur la personne, et — point crucial pour le mentorat
en particulier — il explique le *pourquoi* de la suggestion pour que la personne puisse la généraliser à la
situation suivante, et pas seulement corriger ce cas précis. La distinction avec « simplement correct » compte : un
commentaire techniquement exact, délivré d'une façon qui semble dédaigneuse ou purement critique, peut
être juste et pourtant échouer à son véritable objectif, qui est d'aider quelqu'un à développer un meilleur jugement au fil
du temps, pas seulement de faire corriger cette PR-là.

**Exemple :**

```text
Correct mais peu utile :  "N'attrape pas Exception ici."
Efficace :                "La ligne 42 attrape Exception, donc le timeout en dessous est avalé et le retry
                           ne se déclenche jamais (vu dans l'incident du mois dernier). Attrape IOException ;
                           règle : n'attraper que ce que tu sais traiter à ce niveau."
```

## 🟡 Pièges seniors

### Leadership

#### Q2. Un ingénieur junior commet sans cesse la même catégorie d'erreur malgré des commentaires de code review répétés. Quelle est votre approche concrète ? {#junior-engineer-keeps-making-same}
**Réponse :** D'abord, vérifier si les retours jusqu'ici ont réellement expliqué le principe sous-jacent
ou se sont contentés de corriger le cas précis à chaque fois — répéter « corrige ça » sans le « pourquoi »
réutilisable qui l'accompagne enseigne à reconnaître le motif de ce seul commentaire de review, pas le
jugement généralisable qui préviendrait le *cas suivant*. Avoir une conversation directe et privée — passer
en revue deux ou trois vrais exemples ensemble, lui demander d'articuler le principe sous-jacent
avec ses propres mots, et convenir de quelque chose de concret à essayer différemment à l'avenir. Si le schéma
persiste après une conversation réellement claire et directe, c'est le signal d'impliquer son
manager — mais le premier geste est toujours une vraie conversation axée sur la compréhension, pas une
escalade.

**Exemple :**

```text
PR comment pattern (3 PRs in a row): "missing null check on line 42"
                                       "missing null check on line 88"
                                       "missing null check on line 15"
-> each was fixed individually, none explained *why* this class of input can be null here,
   or how to recognize the pattern before writing the code, not just after review flags it.
```

**Pourquoi c'est un piège :** l'instinct sous la pression de l'entretien est « je continuerais à laisser des commentaires de review
clairs » — la question teste précisément si le candidat reconnaît que des commentaires corrects répétés qui ne portent pas
sont le signe que l'intervention elle-même doit changer, et non se répéter.

#### Q3. Comment contestez-vous une décision technique venant d'une partie prenante senior ou d'un manager que vous jugez erronée ? {#push-back-technical-decision-coming}
**Réponse :** Commencer par une vraie curiosité sur leur raisonnement avant d'affirmer le vôtre — ils peuvent
avoir un contexte que vous n'avez pas (une contrainte métier, une tentative échouée antérieure, une pression de calendrier qui
change le calcul). Énoncer votre préoccupation de façon concrète et précise (le risque ou le coût réel,
idéalement avec une quantification approximative), proposer une alternative précise plutôt que de seulement soulever une
objection, et être explicite sur ce qu'il faudrait voir pour vous faire changer d'avis. Si, après cette
conversation, la décision va tout de même dans l'autre sens et qu'il ne s'agit pas d'un enjeu critique de correction ou de sécurité,
le geste de niveau senior est de s'engager pleinement dans la direction décidée plutôt que de la remettre
sans cesse en cause — « disagree and commit », réservé aux désaccords réellement non critiques.

**Exemple :**

```text
Weak pushback:   "I don't think we should do it this way."
Strong pushback: "This approach adds ~2 weeks of migration risk because it touches the
                  payments schema live. If we instead do X, we lose feature Y for one
                  release but avoid that risk. What would need to be true for the
                  original approach to still be right?"
```

**Pourquoi c'est un piège :** un désaccord vague (« j'ai des inquiétudes ») passe pour de la friction sans substance —
le piège est de s'arrêter à soulever une objection au lieu de l'associer à un coût concret et à une
alternative concrète, ce qui rend la contestation persuasive plutôt que simplement notée.

#### Q4. En tant que tech lead, comment gérez-vous une design review où deux ingénieurs seniors sont fortement en désaccord ? {#tech-lead-handle-design-review}
**Réponse :** Séparer d'abord le désaccord des personnes — s'assurer que les deux se sentent
réellement écoutés, puis faire écrire les deux positions assez concrètement pour les comparer sur les mêmes
axes (que optimise chaque approche, que coûte chacune, dans quel scénario futur
chacune se révélerait avoir été le meilleur choix). Chercher à savoir s'il s'agit d'une décision dont la
bonne réponse est connaissable et atteignable avec plus d'information (un spike, un benchmark) ou d'un vrai compromis de valeurs/
priorités sans réponse objectivement correcte — le premier cas se résout en obtenant l'information
manquante ; le second est un jugement qui a finalement besoin d'un responsable pour trancher, une fois
les deux côtés pleinement entendus, plutôt que d'être laissé à pourrir comme une impasse non résolue.

**Exemple :**

```text
Position A: "Event-sourced — full audit trail, but higher complexity, 3 extra weeks."
Position B: "CRUD + audit table — simpler, ships now, harder to replay history later."

Resolvable by a spike? No — it's a genuine priority trade-off (audit depth vs. time-to-ship)
-> tech lead names the priority for this project explicitly, makes the call, explains why.
```

**Pourquoi c'est un piège :** chercher un consensus total sur un vrai compromis de valeurs peut bloquer un
projet indéfiniment — le piège est de traiter « faire s'accorder tout le monde » comme l'objectif au lieu de « faire
prendre la décision, l'expliquer et en porter la responsabilité », ce dont une review bloquée a réellement besoin.

#### Q5. Comment cadrez-vous et estimez-vous un projet à très forte incertitude pour des parties prenantes qui veulent une date ferme ? {#scope-estimate-project-genuinely-high}
**Réponse :** Être explicite sur le fait qu'une estimation ponctuelle unique pour un projet très incertain est en soi un
mensonge déguisé en précision — communiquer plutôt une fourchette fondée sur les sources réelles
d'incertitude (préciser ce qui est inconnu : une intégration tierce peu familière, une
exigence floue, une dépendance envers un travail non livré d'une autre équipe). Proposer une façon concrète de *réduire*
l'incertitude tôt — un court spike time-boxé sur l'inconnue la plus risquée avant de s'engager sur une
estimation complète. Découper le projet en jalons avec leurs propres points de contrôle, afin que la partie prenante
obtienne un vrai signal sur la conformité du projet à l'estimation bien avant la
date finale.

**Exemple :**

```text
"3-5 weeks. The 2-week spread is entirely the unfamiliar payment-provider integration —
 we haven't confirmed their sandbox supports partial refunds yet. We'll spike that in
 week 1 and can tighten the estimate to +/- 2 days by end of week 1."
```

**Pourquoi c'est un piège :** céder à la pression pour une fausse date précise unique, ou refuser totalement d'estimer,
sont tous deux pires qu'une fourchette avec une cause nommée — le piège est de traiter « donne-moi une date ferme »
comme une demande à laquelle il faut répondre par une date ferme, plutôt que de la recadrer autour de ce qui
génère réellement l'incertitude.

## 🔴 Expert / Ouvert

### Leadership & stratégie

#### Q6. Vous héritez d'une équipe au moral bas et avec une dette technique importante. Décrivez votre approche pour les 90 premiers jours en tant que tech lead. {#inherit-team-low-morale-significant}
**Réponse :** Résister à l'envie de lancer immédiatement de grosses réécritures ou des changements radicaux avant de
comprendre pourquoi les choses en sont arrivées là — les premières semaines servent surtout à écouter : des 1:1 avec
chaque membre de l'équipe, et examiner les incidents/postmortems récents et l'état réel de la base de code
directement plutôt que de s'appuyer uniquement sur un récit de seconde main. Trouver une ou deux victoires concrètes et visibles
atteignables dans le premier mois — pas le plus gros poste de dette technique, mais quelque chose qui
réduit de façon démontrable un vrai irritant quotidien, en bâtissant la confiance que les choses peuvent réellement s'améliorer
avant de demander de la patience pour le travail structurel plus important et plus lent. En parallèle, établir un petit
nombre de pratiques concrètes et légères qui se cumulent avec le temps (un processus de postmortem blameless,
du temps protégé pour la dette technique, une definition of done plus claire), et être explicite et transparent
avec l'équipe sur le plan et le raisonnement derrière les décisions de priorisation. À la fin des 90
jours, le but n'est pas que la dette technique ait disparu — c'est que l'équipe ait confiance qu'un plan
crédible et visible est en cours d'exécution.

**Exemple :**

```text
Weeks 1-2:  1:1s with all 6 engineers + read last 4 postmortems + skim the top 5 hottest files
Week 3:     ship one visible fix for the #1 complaint (flaky CI -> stable in 3 days)
Weeks 4-12: protected 20% time for debt, blameless postmortem template adopted,
            weekly written update on what shipped and why it was prioritized
Day 90:     debt backlog is still long, but every engineer can name what changed and why
```

**Pourquoi c'est un piège :** l'instinct sous la pression de l'entretien est d'ouvrir avec un plan technique audacieux
(une réécriture, une nouvelle architecture) — la question teste si le candidat commence par
l'écoute et une petite victoire qui bâtit la confiance, puisqu'une équipe au moral bas n'adhérera pas à un gros
plan venant de quelqu'un qui n'a pas encore gagné sa crédibilité auprès d'elle.

#### Q7. Comment décidez-vous entre construire un composant vous-même et l'acheter (ou adopter de l'open source) ? {#decide-building-component-yourself-buying}
Le cadrer comme un **coût total de possession sur la durée de vie**, pesé face à la valeur stratégique. Demander d'abord : est-ce un **différenciateur** — quelque chose qui donne au produit un avantage
concurrentiel — ou une **commodité** (authentification, paiements, livraison d'emails, observabilité, recherche) ? Les capacités de commodité favorisent presque toujours l'achat ou l'adoption : le fournisseur
a déjà consacré des milliers d'années-ingénieur aux cas limites, à la conformité (PCI, SOC 2, GDPR) et aux correctifs de sécurité, et le temps rare de vos ingénieurs va à
ce que seule votre entreprise peut construire. Construire quand c'*est* le différenciateur, quand aucun produit ne satisfait les contraintes (latence, résidence des données, échelle inhabituelle), ou quand le vendor lock-in et la tarification
à votre échelle feraient plus mal que le coût d'ingénierie. Inclure le coût complet de chaque option : pour **construire** — développement initial, maintenance continue et on-call, charge de sécurité
et de montées de version, recrutement de personnes qui le comprennent, et coût d'opportunité de ce que ces personnes n'ont pas construit ; pour **acheter** — frais de licence ou d'usage qui croissent avec le volume (modéliser le
prix à 10× le trafic), effort d'intégration, **lock-in et coût de sortie** (export de données, différences d'API), stabilité du fournisseur, SLA, et flexibilité perdue. Réduire le risque de l'achat en isolant le fournisseur derrière
votre propre interface mince (un adapter ou une couche anti-corruption), en gardant les données portables, et en menant une preuve de concept time-boxée face à vos vraies exigences. Réduire le risque de la construction en
commençant par la plus petite version et en réévaluant : un composant maison devenu un fardeau de maintenance sans valeur différenciante est un signal pour le remplacer par un produit, et un
fournisseur dont les coûts ou contraintes dominent désormais est un signal pour le rapatrier en interne. Consigner la décision et ses hypothèses (un ADR) avec une date de réexamen, pour que l'équipe puisse dire plus tard si le raisonnement tient toujours.

**Exemple :**

```text
ADR-014 : Acheter l'envoi d'emails transactionnels (SES + port EmailSender) plutôt que construire
Contexte :  capacité de commodité, 2M mails/mois, 1 ingénieur en serait responsable
Options :   construire un pipeline SMTP (~3 mois-ingénieur + on-call) | acheter (~200 $/mois, ~2 k$/mois à 10x)
Décision :  acheter ; fournisseur masqué derrière EmailSender, templates dans notre repo (coût de sortie ~1 semaine)
Réexamen :  03/2027 ou si coût mensuel > 5 k$
```

#### Q8. Comment menez-vous la coordination d'un incident majeur en production ? {#run-incident-command-during-major}
**Réponse :** Séparer les rôles pour que personne ne débogue et ne coordonne à la fois : un **incident commander** qui prend les décisions sans toucher au clavier, un ou plusieurs **intervenants** qui investiguent, et un **communicant** qui tient les parties prenantes informées.

Atténuer d'abord (rollback, feature flag, failover), chercher la cause racine ensuite.

Limiter chaque hypothèse dans le temps, consigner les décisions dans un seul canal, publier des points d'étape à cadence fixe même sans nouveauté, et écrire la timeline au fil de l'eau pour que le postmortem soit presque fait à la clôture.

**Exemple :**

```text
#inc-2417  IC : Sam   Ops : Lea   Comms : Omar
14:02 IC : SEV1 déclaré - checkout en 5xx à 40 %. Lea : regarde les déploiements + la BDD. Omar : status page sous 10 min.
14:09 Lea : le déploiement 1.84 est parti à 13:55, p99 de payments-db x3.
14:10 IC : décision - rollback de 1.84 maintenant ; on investigue après l'atténuation. Objections ? Aucune.
14:16 Lea : rollback fait, 5xx à 2 %. IC : on garde le SEV1 15 min pour confirmer.
14:20 Omar -> status page : "Checkout dégradé 13:55-14:16, corrigé. Prochain point 14:45 ou en cas de changement."
```

**Pourquoi c'est un piège :** les candidats décrivent un débogage héroïque ; la question teste si l'on coordonne, atténue avant de diagnostiquer et communique à cadence régulière.

#### Q9. Comment rédigez-vous une RFC ou un ADR pour qu'une équipe décide vraiment, au lieu de débattre sans fin ? {#write-rfc-adr-team-decides}
**Réponse :** Poser le problème et les contraintes avant la solution, lister au moins deux vraies alternatives avec leurs coûts honnêtes (y compris « ne rien faire »), donner une recommandation, fixer une date limite de décision et un décideur nommé.

Rester court (1-2 pages), faire circuler d'abord en commentaires asynchrones, et réserver la réunion aux points non résolus.

Consigner la décision et les raisons pour lesquelles elle pourrait être revue, afin que les futurs lecteurs comprennent qu'il s'agissait d'un jugement sous hypothèses connues.

**Exemple :**

```text
RFC-07 : Déplacer le stockage des sessions de la BDD vers Redis    Décideuse : Dana   Décision avant : ven. 12
Problème :    les lectures de sessions = 38 % de la charge de la BDD primaire ; p95 du login = 900 ms en pic
Options :     A) ne rien faire (réplica de lecture, ~900 $/mois, gagne ~6 mois)
              B) Redis (nouvelle infra, ~2 semaines, cible p95 < 150 ms)
              C) JWT signés (pas de store, mais pas de révocation côté serveur)
Recommandé :  B. Risque : panne Redis = tout le monde déconnecté -> réplica + grâce de 30 s.
Points ouverts : TTL de session ; qui est d'astreinte pour Redis ?
```

**Pourquoi c'est un piège :** un long document avec une seule option et sans décideur est une annonce de design, pas un outil de décision.

#### Q10. Comment structurez-vous le recrutement et les entretiens pour des décisions cohérentes et équitables ? {#structure-hiring-interviewing-decisions-consistent}
**Réponse :** Définir le niveau et les signaux recherchés avant d'interviewer (ex. débogage, compromis de conception, collaboration), confier un signal à chaque interviewer, utiliser les mêmes questions et une grille écrite pour tous les candidats, et demander les retours écrits *avant* le débrief pour que la voix la plus forte n'ancre pas le groupe.

Les faits (« elle a identifié la race condition sans aide ») valent mieux que l'impression (« a l'air intelligent »). L'expérience candidat fait partie du travail : planning clair, réponse rapide.

**Exemple :**

```text
Grille - Backend senior, signal « débogage » (1 = aucun signal, 4 = fort)
 1  a besoin d'indices à chaque étape      3  formule des hypothèses, cible avec logs/métriques
 2  devine, change plusieurs choses        4  propose aussi la prévention (alerte, test)
Fiche de retour : note + 2 observations concrètes + « serais-je content de l'avoir dans mon équipe ? pourquoi »
Débrief : lecture silencieuse des fiches (5 min) -> chacun donne sa note d'abord -> on ne discute que des désaccords
```

**Pourquoi c'est un piège :** « je me fie à mon instinct » signale incohérence et biais.

#### Q11. Comment déléguez-vous bien, et comment dites-vous non sans abîmer la relation ? {#delegate-well-say-damaging-relationship}
**Réponse :** Déléguer le résultat, pas les étapes : énoncer l'objectif, les contraintes, les droits de décision et les points de contrôle, puis laisser la personne choisir l'approche.

Adapter la tâche à un axe de progression tout en gardant un filet de sécurité (une revue à mi-parcours).

Pour dire non : reconnaître l'objectif derrière la demande, donner le compromis en termes concrets (ce qui glisse si on dit oui), proposer une alternative ou une date ultérieure. Un non avec une raison et une option est une négociation, pas un refus.

**Exemple :**

```text
Délégation :   "Tu portes la migration de l'export de facturation vers la nouvelle file. Terminé = zéro facture
                perdue sur 1 semaine en shadow. Tu décides du déploiement ; préviens-moi avant la bascule.
                Point jeudi : design en 1 page."
Dire non :     "Je ne peux pas prendre la demande de dashboard ce sprint sans abandonner le correctif SSO, qui
                bloque 3 clients. Je peux faire une version basique au prochain sprint, ou commencer maintenant
                si tu me dis lequel cède."
```

**Pourquoi c'est un piège :** « je le ferais moi-même » (ne sait pas déléguer) et « je dirais oui et je travaillerais la nuit » (ne sait pas dire non) sont les deux défauts sondés.

#### Q12. Comment intégrez-vous un nouvel ingénieur pour qu'il soit rapidement productif ? {#onboard-new-engineer-productive-quickly}
**Réponse :** Préparer avant le jour 1 : laptop, accès, un binôme, un plan écrit. Viser un petit changement réel en production dès la première semaine (donne confiance et valide l'environnement), puis élargir progressivement le périmètre.

Donner du contexte, pas seulement des tâches : vue d'architecture, qui possède quoi, pourquoi les décisions clés ont été prises. Tenir des 1:1 réguliers, recueillir les retours sur l'onboarding lui-même, et corriger la doc chaque fois qu'un arrivant bute.

**Exemple :**

```text
Jour 1      laptop + accès prêts, rencontre du binôme, lancer l'app en local
Semaine 1   livrer un petit ticket en production (typo/log/flag), lire 3 ADR clés
Jour 30     porte une petite fonctionnalité de bout en bout, a observé une astreinte
Jour 60     relit des PR sur un périmètre, première astreinte avec un binôme en soutien
Jour 90     rétro avec le manager : qu'est-ce qui était flou ? -> 3 corrections de doc mergées par l'arrivant
```

**Pourquoi c'est un piège :** « je lui donne la doc et il lit » ignore que le meilleur signe d'équipe saine est la vitesse à laquelle un arrivant livre quelque chose de réel.

#### Q13. Comment gérez-vous la relation avec votre manager (« manage up ») sans surprises ? {#manage-up-keeping-manager-informed}
**Réponse :** Convenir explicitement des priorités et des critères de succès, puis communiquer de façon proactive : mauvaises nouvelles tôt avec un plan proposé, avancement à cadence régulière, décisions attendues avec une échéance.

Parler en résultats et en risques, pas en activité. Demander sur quoi le manager est évalué pour que votre travail s'y rattache. Le but : que votre manager ne soit jamais surpris par ce qu'il aurait pu apprendre de vous.

**Exemple :**

```text
Point hebdo (5 lignes) :
Fait :      retry paiements livré, charges échouées -18 %
Ensuite :   migration SSO (démarre lundi)
Risque :    sandbox fournisseur instable -> +3 jours possibles ; confirmation mercredi
Besoin :    décision jeudi : abandonner l'export CSV legacy ou le garder (coût : 4 jours)
Aide :      intro à l'équipe sécurité pour le créneau de pentest
```

**Pourquoi c'est un piège :** « je fais du bon travail et ça se voit » laisse le manager aveugle ; le réflexe senior est de rendre avancement et risques visibles.

#### Q14. Comment mesurer si votre équipe livre bien, sans transformer les métriques en objectifs ? {#measure-whether-team-delivering-well}
**Réponse :** Utilisez les quatre **métriques DORA** comme vue d'ensemble du système : fréquence de déploiement, délai de mise en production des changements, taux d'échec des changements, et temps de rétablissement du service.

Elles équilibrent vitesse et stabilité : améliorer l'une au détriment de l'autre se voit.

Lisez-les comme des tendances pour l'équipe et le système de livraison, jamais par personne, et associez-les à des signaux qualitatifs : enquêtes sur l'expérience développeur (cadre SPACE), charge d'astreinte, et fréquence à laquelle l'équipe tient ses engagements.

Servez-vous-en pour trouver les goulets (« le délai est de 9 jours, dont 6 à attendre une revue »), pas pour classer les gens.

Dès qu'un chiffre devient un objectif, on optimise le chiffre (découper les PR pour gonfler le nombre de déploiements) ; discutez donc de l'histoire derrière le chiffre en rétro.

**Exemple :**

```text
Trimestre      Déploiements/sem.  Délai    Échec des changements  Rétablissement
T1             3                  9 jours  22 %                   5 h
T2 (actions : SLA de revue 1 jour, feature flags, PR plus petites, canary)
               11                 2 jours  9 %                    40 min
```

**Pourquoi c'est un piège :** comparer des équipes ou des individus sur les chiffres DORA récompense la triche et pénalise les équipes aux systèmes plus difficiles ; la comparaison utile est celle d'une équipe avec son propre passé.

#### Q15. Comment prioriser la dette technique face au travail produit ? {#prioritise-technical-debt-against-product}
**Réponse :** Rendez la dette visible et chiffrée en termes métier, puis arbitrez-la comme tout autre travail.

Tenez un court registre de dette où chaque élément indique ce qu'il coûte aujourd'hui (incidents, livraison plus lente dans cette zone, temps d'intégration, risque de sécurité ou de montée de version) et ce que sa correction débloquerait.

Priorisez selon le **coût du retard × la fréquence de changement de la zone** : la dette dans du code que personne ne touche peut attendre ; celle du module de paiement que l'équipe modifie chaque semaine, non.

Combinez une capacité permanente (souvent 15–20 % par sprint) pour les petites corrections continues avec des éléments explicites de roadmap pour les gros chantiers, présentés avec un business case.

Corrigez au passage quand une fonctionnalité touche le code (« laisser le code meilleur »), et posez des garde-fous (lint, ArchUnit, mises à jour de dépendances) pour que la nouvelle dette ne s'accumule pas.

**Exemple :**

```text
Élément                      Douleur actuelle                       Fréq. de changement  Proposition
Module de tarification       3 incidents/trim., features 2x plus lentes  hebdomadaire   Roadmap T3 : strangler, 4 semaines
Spring Boot 2 -> 3           fin de support, CVE non corrigées      n/a                  Obligatoire, 2 sprints, date fixée
Ancien back-office (jQuery)  laid, mais stable                      deux fois par an     On laisse ; à revoir s'il change
```

**Pourquoi c'est un piège :** demander « un sprint de refactoring » sans chiffres ressemble à des développeurs qui veulent peaufiner leur code, et perd face à n'importe quelle fonctionnalité ; le même travail présenté comme « réduire les incidents du paiement et diviser par deux le délai sur la tarification » est en général accepté.

#### Q16. Comment animer une rétrospective qui débouche sur des changements ? {#run-retrospective-leads-change}
**Réponse :** Gardez-la sûre et sans recherche de coupable : l'animateur rappelle l'objectif (améliorer notre façon de travailler, pas juger les personnes) et s'assure que les personnes discrètes sont entendues, par exemple avec un temps d'écriture silencieuse avant la discussion.

Partez des données : ce qui s'est passé pendant le sprint ou l'incident, métriques, chronologie. Regroupez les sujets, votez, et consacrez l'essentiel du temps aux un ou deux qui comptent, en creusant les causes.

Terminez par **peu d'actions concrètes**, chacune avec un responsable et une date, et commencez la rétro suivante en les passant en revue.

Variez le format de temps en temps (start/stop/continue, 4L, frise chronologique) pour éviter la routine, et faites remonter les problèmes que l'équipe ne peut pas résoudre seule au lieu d'en reparler à chaque fois.

**Exemple :**

```text
Sujet (5 votes) : « les livraisons glissent parce que la QA commence au jour 9 »
Cause : des stories trop grosses pour être testées avant la fin du sprint
Action : découper les stories pour que chacune soit testable en ≤ 2 jours ; Sam porte la checklist d'affinage ; revue à la prochaine rétro
```

**Pourquoi c'est un piège :** une rétro qui produit dix actions vagues (« mieux communiquer ») sans jamais les vérifier apprend à l'équipe que les rétros ne changent rien, et les gens arrêtent de s'exprimer.

## 🎯 Scénarios réels

### S1. Une design review entre deux ingénieurs seniors bloque un projet pendant des semaines sans résolution {#design-review-two-senior-engineers}
- **Symptômes :** Deux ingénieurs seniors ont des positions fermes et opposées sur une décision
  d'architecture centrale, et des réunions de review répétées ne convergent pas — le calendrier du projet glisse
  pendant que le désaccord continue.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** En tant que tech lead qui relit cela, vérifier si le désaccord porte réellement sur
  un fait technique connaissable (résoluble avec un spike/benchmark) ou sur une différence non dite de ce que
  chacun optimise (Q4) — un désaccord bloqué persiste souvent précisément parce que
  aucun des deux camps n'a identifié qu'il argumente à partir de priorités différentes et non dites.
- **Exemple :**

  ```text
  Week 1: review meeting -> no resolution, "let's discuss again next week"
  Week 2: same two positions restated, no new information surfaced
  Week 3: project owner asks each engineer to write down what their approach optimizes
          for -> reveals a genuine time-to-ship vs. long-term-flexibility trade-off, not a
          resolvable factual disagreement -> tech lead makes the call the same day
  ```

- **Résolution :** Faciliter une conversation qui rend explicites et comparables les vrais compromis des deux positions,
  obtenir directement la réponse à toute question factuelle résoluble, et s'il s'agit réellement d'un
  jugement sans réponse objectivement juste, trancher explicitement en tant que responsable de la décision.
- **Prévention :** Établir un processus de décision clair (qui a le dernier mot, et dans quelles
  circonstances un spike time-boxé tranche un désaccord) avant le début d'un projet, pour qu'un vrai
  désaccord ait un chemin de résolution connu plutôt que de dégénérer par défaut en débat sans fin.

</details>

### S2. Les PR d'un ingénieur junior répètent la même catégorie d'erreur malgré les commentaires de review {#junior-engineer-prs-keep-repeating}
- **Symptômes :** Les commentaires de code review identifient correctement la même classe de problème sur plusieurs
  PR consécutives du même ingénieur, corrigée individuellement à chaque fois mais réapparaissant dans la PR
  suivante.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Selon Q2 — les commentaires de review corrigent des cas, ils ne construisent pas le
  jugement sous-jacent qui préviendrait le *cas suivant* ; un schéma de récurrence malgré des retours
  corrects répétés signifie généralement que le « pourquoi » n'a pas réellement porté, pas que la personne
  n'écoute pas.
- **Exemple :**

  ```text
  PR #212 review comment: "missing null check here"
  PR #219 review comment: "same issue as #212 — missing null check"
  PR #227 review comment: "third time — let's talk"  <- direct 1:1 held after this, not #212
  ```

- **Résolution :** Avoir la conversation directe axée sur les principes de la Q2 plutôt qu'un autre commentaire
  de PR — passer en revue ensemble plusieurs vrais exemples, lui faire réexpliquer le principe sous-jacent
  avec ses propres mots, et convenir d'une pratique concrète pour la suite.
- **Prévention :** Pour toute catégorie d'erreur apparaissant plus de deux fois chez la même personne,
  passer proactivement des commentaires de PR à une conversation directe, plutôt que d'attendre qu'elle
  devienne un schéma manifestement enraciné.

</details>

### S3. Le moral de l'équipe chute visiblement après un licenciement ou une réorganisation, et la productivité/la confiance en souffrent {#team-morale-visibly-drops-after}
- **Symptômes :** Les membres restants de l'équipe montrent un engagement réduit, un scepticisme accru envers la
  communication de la direction, et un ralentissement notable de la livraison au-delà de ce que la seule réduction d'effectif
  expliquerait.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** L'érosion de la confiance après un licenciement/une réorganisation est une réaction normale et attendue, pas un
  problème de discipline — les gens traitent l'incertitude sur leur propre sécurité et le deuil de
  collègues/de relations de travail qui ont changé.
- **Exemple :**

  ```text
  Before reorg: sprint velocity ~40 pts, Slack activity in #team normal
  2 weeks after: velocity ~22 pts, 1:1s reveal 4/6 remaining engineers are job-searching,
                 standup updates get noticeably shorter and less detailed
  ```

- **Résolution :** Sur-communiquer, honnêtement, plus qu'il ne semble nécessaire — reconnaître directement ce qui
  s'est passé, être transparent sur ce qui est et n'est pas connu de l'avenir, et rebâtir
  la prévisibilité par des engagements plus petits et constants tenus de façon fiable, plutôt que par un grand
  geste censé « réparer » le moral.
- **Prévention :** C'est en grande partie non évitable au niveau d'un manager individuel une fois qu'une décision de
  licenciement/réorganisation est prise au-dessus de lui, mais le schéma de communication constant et honnête d'un manager
  *avant* un tel événement est ce qui détermine la quantité de confiance résiduelle sur laquelle
  rebâtir.

</details>

### S4. Une partie prenante exige une deadline irréaliste pour une fonctionnalité complexe {#stakeholder-demands-unrealistic-deadline-complex}
- **Symptômes :** Une partie prenante énonce une deadline ferme pour une fonctionnalité que l'équipe d'ingénierie estime
  nécessiter sensiblement plus de temps, la deadline étant apparemment non négociable d'après
  le cadrage de la partie prenante.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Avant de supposer que la deadline elle-même est la contrainte immuable, clarifier ce qui est
  réellement à l'origine de celle-ci (un engagement externe réel versus un objectif choisi en interne, plus
  flexible qu'il n'y paraît) et clarifier séparément si le *périmètre* est vraiment figé.
- **Exemple :**

  ```text
  Stakeholder: "This needs to ship by the 30th, no exceptions — it's tied to a partner launch."
  Follow-up: "Is the 30th the partner's hard date, or our internal target for it?"
  Answer: "...it's actually our target, the partner's real cutoff is 6 weeks later."
  -> the "non-negotiable" deadline had 6 weeks of hidden slack once actually asked about.
  ```

- **Résolution :** Présenter explicitement le vrai compromis — « voici ce qui tient d'ici cette date, voici
  ce qui devrait être reporté à un suivi, voici le risque si on le comprime à la place » — et laisser la
  partie prenante prendre une décision éclairée, en utilisant l'approche d'estimation sous incertitude de la Q5 si le
  périmètre lui-même est encore flou.
- **Prévention :** Bâtir avec les parties prenantes récurrentes une relation de travail où les compromis de périmètre et de
  calendrier sont une partie normale et attendue de la conversation dès le début de tout
  projet, plutôt que de laisser la première conversation de ce type avoir lieu sous pression de deadline.

</details>

### S5. Deux membres de l'équipe sont en conflit permanent sur la propriété du code ou l'approche technique {#two-team-members-ongoing-conflict}
- **Symptômes :** Frictions répétées en review ou en planification entre deux membres précis de l'équipe,
  qui dépassent le désaccord technique normal pour devenir une dynamique personnelle ou territoriale qui
  commence à affecter la dynamique de l'équipe élargie.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Distinguer un désaccord technique réel et résoluble (le domaine de la Q4) d'une
  rupture de relation/de communication qui s'exprime par des désaccords
  techniques — le second cas demande une intervention différente de davantage de discussions techniques.
- **Exemple :**

  ```text
  Reviewer A (1:1): "I keep getting blocked because B rewrites my PRs in review instead of
                      commenting."
  Reviewer B (1:1): "A's code doesn't follow the patterns we agreed on, so I just fix it
                      myself to keep things moving."
  -> both are reacting to a missing shared review norm, not to each other personally.
  ```

- **Résolution :** Avoir d'abord des conversations 1:1 séparées avec chaque personne, puis, si approprié, une
  conversation commune facilitée centrée sur la relation de travail et les normes de communication pour la
  suite, sans remettre en cause les désaccords techniques précis qui l'ont déclenchée.
- **Prévention :** Traiter la friction tôt, dès le premier signe d'un schéma plutôt qu'après qu'il
  affecte visiblement l'équipe élargie — une conversation privée et à faible enjeu tôt est bien plus facile qu'
  une médiation plus lourde après des semaines de friction accumulée.

</details>

### S6. Un incident de production remonte à une décision d'architecture que vous avez personnellement prise {#production-incident-traces-back-architectural}
- **Symptômes :** Une enquête de postmortem identifie la cause racine comme un choix de conception précis
  que vous avez défendu et pris, et non un bug sans rapport ou un facteur extérieur.
- **Diagnostic/réflexion :** C'est un moment où la façon dont vous le gérez compte autant que le
  correctif technique — minimiser votre propre rôle, ou à l'inverse s'excuser à outrance au point de détourner
  le véritable objectif du postmortem, sont tous deux moins utiles qu'un compte rendu clair et factuel de la
  décision et de ce qui est différent aujourd'hui pour que le résultat soit visible.
- **Exemple :**

  ```text
  Postmortem timeline entry, written by the decision-maker themselves:
  "2026-02-11: I chose async replication for the orders DB to hit the launch date,
   accepting the RPO trade-off documented in ADR-014. That trade-off is what caused
   today's data loss on failover. The information available in Feb didn't include our
   current write volume."
  ```

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Résolution :** Assumer la décision simplement sans rejeter la faute ailleurs, centrer la
  discussion sur le véritable but du postmortem blameless (quel facteur systémique a permis ce résultat,
  et quels changements réduisent le risque d'une erreur similaire de la part de quiconque à l'avenir), et assurer
  visiblement le suivi des actions convenues.
- **Prévention :** Une équipe qui a vu son tech lead gérer sa propre erreur de cette façon bâtit
  bien plus de confiance dans le processus de postmortem blameless qu'une équipe qui ne l'a vu appliqué qu'aux
  autres — ce moment précis a une influence disproportionnée sur la question de savoir si l'équipe croit réellement
  que le processus est blameless en pratique.

</details>

### S7. Une rotation d'astreinte se noie sous des pages non actionnables, et l'équipe cesse de faire assez confiance aux alertes pour réagir vite à une vraie {#call-rotation-drowns-non-actionable}
- **Symptômes :** La rotation d'astreinte reçoit des dizaines de pages par semaine, dont la grande majorité
  se résolvent d'elles-mêmes ou ne demandent aucune action ; les ingénieurs signalent qu'ils mettent en sourdine ou retardent les pages, et un
  incident réellement critique est récemment resté non acquitté pendant plus de 20 minutes parce qu'il ressemblait à du
  bruit de routine.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Extraire le dernier mois de pages et catégoriser chacune comme actionnable (a nécessité une réponse
  humaine) vs non actionnable (résolue d'elle-même, en flapping, ou symptomatique d'un problème connu, déjà suivi)
  — un ratio élevé de non actionnables est la cause directe de la désensibilisation, pas un problème de
  discipline de la personne d'astreinte.
- **Exemple :**

  ```text
  Last 30 days: 214 pages fired
    - 6   required actual human intervention
    - 91  self-resolved within 2 minutes (flapping health check, no action needed)
    - 117 duplicate/downstream alerts for one root-cause incident, firing separately
  -> signal-to-noise ratio ~2.8%, and the one incident that mattered was buried in it
  ```

- **Résolution :** Réajuster les seuils d'alerte selon l'actionnabilité réelle, ajouter de la déduplication/du
  regroupement d'alertes pour qu'une cause racine déclenche une page au lieu de plusieurs, et supprimer ou rétrograder en
  non-paging toute alerte qui n'a nécessité aucune action dans la fenêtre de revue.
- **Prévention :** Revoir les alertes de paging selon leur actionnabilité réelle à cadence régulière, et
  traiter « cette page a-t-elle exigé qu'un humain fasse réellement quelque chose » comme le critère pour la garder en
  page, plutôt qu'en ticket ou en métrique de dashboard.

*Voir aussi :* [Full Stack S22](fullstack-devops-k8s.md#call-phone-rings-dozens-times) pour le côté technique : alertes basées sur les SLO et sur les symptômes.

</details>

### S8. Un membre de l'équipe réagit systématiquement de façon défensive aux retours de code review, quelle que soit la manière dont ils sont formulés {#team-member-consistently-responds-defensively}
- **Symptômes :** Des retours de review raisonnables et bien formulés se heurtent de façon répétée à des objections,
  des justifications ou une frustration visible d'un membre précis de l'équipe, même quand le retour est
  factuellement correct et délivré de façon constructive par plusieurs relecteurs différents.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Une défensive constante chez plusieurs relecteurs et plusieurs styles de formulation
  suggère que le problème ne tient pas vraiment à la façon dont le retour est formulé — il tient plus probablement à la façon dont la
  personne vit le feedback en général.
- **Exemple :**

  ```text
  Reviewer A: "consider extracting this into a helper" -> pushback + justification thread
  Reviewer B: "nit: this could be simplified" -> same pattern, different reviewer, same person
  Reviewer C (different team, first time reviewing this person): same pattern again
  -> consistent across reviewers and phrasing rules out "it's how it's being said."
  ```

- **Résolution :** Avoir une conversation directe, privée et curieuse (non accusatrice) portant spécifiquement sur
  le schéma lui-même, séparée de toute PR précise, et par ailleurs s'assurer que la culture de review de l'équipe
  elle-même n'y contribue pas involontairement.
- **Prévention :** Établir tôt des normes et attentes de review claires et partagées dans l'équipe, pour que
  la réaction d'un individu au feedback porte plus probablement sur le contenu précis que sur un
  standard ambigu ou appliqué de façon incohérente.

</details>

### S9. Une dépendance inter-équipes bloque de façon répétée la livraison de votre équipe {#cross-team-dependency-repeatedly-blocks}
- **Symptômes :** La roadmap de votre équipe continue de glisser parce qu'un travail requis d'une autre
  équipe n'est pas prêt quand il le faut, de façon récurrente sur plusieurs projets et non comme un raté
  ponctuel de planning.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Un schéma récurrent suggère un problème structurel — les priorités ne sont pas réellement
  alignées entre les équipes, ou il n'existe pas de processus clair pour négocier et s'engager sur des
  éléments de travail inter-équipes avec une vraie responsabilité.
- **Exemple :**

  ```text
  Project Alpha: slipped 3 weeks waiting on Team Y's export API
  Project Beta (2 months later): slipped 2 weeks waiting on the same Team Y, different API
  -> a recurring pattern with the same team, not a one-off scheduling miss
  ```

- **Résolution :** Escalader pour rendre la dépendance et son impact métier visibles à un niveau où
  les priorités des deux équipes peuvent réellement être conciliées, en apportant un impact concret et chiffré plutôt
  qu'une plainte vague du type « on est bloqués ».
- **Prévention :** Pour les dépendances inter-équipes connues et récurrentes, établir un processus explicite de
  priorisation/d'engagement avant que le prochain projet n'en ait besoin, plutôt que des demandes informelles
  sans véritable mécanisme pour être honorées face à des priorités concurrentes.

</details>

### S10. Retirer un système legacy dont dépendent encore de nombreuses équipes s'avère bien plus difficile que prévu {#sunsetting-legacy-system-many-teams}
- **Symptômes :** Une dépréciation planifiée d'un ancien système cale à répétition — les équipes ont toujours « encore
  une » dépendance qui n'est pas prête à migrer, et la date de sunset ne cesse de glisser.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Le plan a probablement sous-estimé le périmètre réel des dépendants et/ou n'a pas donné aux
  équipes dépendantes assez d'incitation ou de soutien pour prioriser réellement leur travail de migration face à
  la pression de leur propre roadmap.
- **Exemple :**

  ```text
  known dependents at planning time: 4 services
  actual dependents discovered mid-migration: 11 services, including one found only
  because it started throwing errors the week the legacy write path was deprecated
  ```

- **Résolution :** Faire un audit de dépendances réellement approfondi avant de s'engager sur une date ferme,
  fournir un soutien concret à la migration (outillage, documentation, aide directe d'ingénierie pour les
  migrations les plus difficiles), et envisager un sunset par étapes qui fait remonter les dépendants oubliés
  plus tôt et de façon moins catastrophique.
- **Prévention :** Pour tout futur système censé avoir une large adoption interne, intégrer dès le début de sa vie
  l'outillage de dépréciation/migration et le suivi des dépendances, et non comme une
  réflexion après coup quand le sunset devient nécessaire des années plus tard.

</details>

### S11. En tant qu'intervieweur, vous devez évaluer équitablement la réponse d'un candidat en system design {#interviewer-need-evaluate-candidate-system}
- **Symptômes :** Un candidat produit une conception avec un diagramme d'apparence raisonnable, mais vous devez
  évaluer si elle reflète réellement un solide jugement en system design ou des réponses
  mémorisées, toutes faites, qui ne démontrent pas une vraie compréhension.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Le signal le plus fort n'est pas de savoir s'il a dessiné le « bon » diagramme — c'est de savoir s'il
  a posé des questions de clarification avant de concevoir ([System Design Q1](system-design.md#steps-follow-system-design-interview)), s'il sait articuler le vrai
  compromis derrière chaque décision importante, et s'il sait approfondir au moins un
  composant quand on le pousse.
- **Exemple :**

  ```text
  Candidate proposes fan-out-on-write for the whole feed design, no mention of celebrity
  accounts. Interviewer: "This account has 50M followers — walk me through what happens
  when they post."
  Strong candidate: adapts live, proposes the fan-out-on-read special case ([System Design Q42](system-design.md#design-instagram-feed-high-level)).
  Weak candidate: repeats the original design unchanged, doesn't register the new constraint.
  ```

- **Résolution :** Pousser spécifiquement sur les compromis (« pourquoi ceci et pas X ») plutôt que d'accepter une
  conception énoncée telle quelle, et introduire une contrainte modifiée en cours d'entretien pour voir si
  le candidat sait adapter sa conception et son raisonnement en direct.
- **Prévention :** Calibrer les attentes et les grilles des intervieweurs autour du raisonnement sur les compromis et de
  l'adaptabilité spécifiquement, et non de la complétude du diagramme ou de la conformité à une architecture de référence « correcte » précise.

</details>

### S12. Le produit ne veut que des fonctionnalités ; l'ingénierie dit que la dette technique ralentit tout le monde — et la direction ne finance pas le nettoyage {#product-wants-features-only-engineering}
- **Symptômes :** Le lead time par fonctionnalité a doublé en un an, les incidents se répètent dans le même module legacy, et les meilleurs ingénieurs râlent sur « le code
  de facturation ». Chaque demande de « sprint de refactoring » est refusée comme un coût non chiffré sans valeur client.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Le problème est généralement la **communication et la priorisation**, pas un manque de bonne volonté : la dette est décrite en termes d'ingénierie (« c'est le bazar ») que
  le métier ne peut pas peser face aux fonctionnalités. Rassembler des preuves : la part de chaque sprint consacrée aux reprises et corrections de bugs dans ce module, le cycle time et le taux d'échec des changements avant et
  après, le nombre d'incidents et le coût qui lui est imputable, le temps d'onboarding, et les fonctionnalités qu'elle a *bloquées ou retardées*. Identifier quelle dette porte des intérêts (sur le chemin du travail à venir de la roadmap)
  versus la dette laide mais stable qu'on peut laisser tranquille (l'approche des 90 jours de la Q6).
- **Exemple :**

  ```text
  Billing module, last 2 quarters:
    31% of bug tickets, 4 of 6 Sev-2 incidents, median PR lead time 9 days (vs 2 days elsewhere)
    Q3 roadmap: 3 of 5 planned features touch it  ->  estimated 6 weeks of extra work if untouched
  ```

- **Résolution :** La présenter comme un business case : coût du retard et risque versus un investissement borné (« 3 semaines maintenant économisent ~6 semaines au T3 et suppriment la principale
  source de Sev-2 »). Proposer une approche incrémentale qui continue de livrer — refactorer *dans le cadre* des fonctionnalités de la roadmap qui touchent la zone, protéger une part fixe de capacité
  (10–20 %) pour la dette avec des métriques convenues, ou une approche strangler — plutôt qu'un « on arrête les fonctionnalités pendant un trimestre » en big-bang. Convenir de mesures de succès et les réexaminer.
- **Prévention :** Suivre la dette explicitement (un registre visible avec impact et coût du retard), intégrer les métriques de qualité aux revues produit régulières, appliquer la règle du « boy scout »
  au quotidien, et maintenir les responsables de l'ingénierie et le produit dans une conversation permanente sur l'allocation de capacité plutôt qu'une négociation en temps de crise.

</details>

### S13. La production et la qualité d'un ingénieur ont baissé sur plusieurs mois, et l'équipe le remarque {#engineer-output-quality-have-dropped}
- **Symptômes :** Un ingénieur auparavant fiable manque désormais ses engagements, ses PR sont en retard et peu soignées, il est plus silencieux en réunion, et ses collègues commencent discrètement à
  le contourner. Personne ne l'a soulevé directement.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Ne pas supposer un « problème de performance » — d'abord découvrir **ce qui a changé** : le travail de la personne (inadéquation de rôle ou de compétence, attentes floues, un
  projet non souhaité), l'environnement (une réorganisation, un nouveau manager, des priorités floues, une dynamique toxique, un blocage par d'autres équipes) ou sa vie (santé, burn-out, famille). Avoir un
  one-to-one privé et curieux (avant tout processus formel) en posant des questions ouvertes et en regardant les faits : exemples précis d'attentes non tenues, comment on en est arrivé là, si les objectifs étaient clairs, si
  la charge de travail est réaliste. Comparer aux attentes que la personne a réellement reçues, pas à un niveau implicite.
- **Exemple :**

  ```text
  1:1 opening: "I've noticed the last three deliverables slipped and you seem less engaged than usual.
                I want to understand what's going on and how I can help - what's your view?"
  -> reveals: moved to a legacy project against their wishes + no clear ownership since the reorg
  ```

- **Résolution :** Selon la cause : clarifier par écrit les attentes et la propriété, lever les blocages, ajuster le travail ou apporter du soutien (congés, charge réduite
  s'il s'agit d'une situation personnelle, coaching ou pairing pour une lacune de compétence), et convenir d'**objectifs spécifiques et mesurables avec une cadence de suivi** (p. ex. hebdomadaire pendant 4–6 semaines). Documenter les conversations. S'il
  n'y a pas d'amélioration malgré des attentes claires et un soutien réel, impliquer les RH/le manager et passer à un plan d'amélioration formel — avec dignité, et avec une communication honnête sur les issues possibles. Vérifier
  les progrès par rapport aux objectifs convenus, pas aux impressions.
- **Prévention :** 1:1 réguliers et feedback précoce et précis pour que les problèmes émergent en semaines, pas en trimestres ; attentes explicites par niveau ; guetter les signes de burn-out ; et traiter le problème directement au lieu de laisser
  l'équipe compenser en silence, ce qui érode la confiance de tous les autres.

</details>

## 🗣️ Comportemental (STAR) {#behavioral-star}

> Les questions comportementales (« Parlez-moi d'une fois où… ») évaluent le jugement, l'ownership et la communication à partir du comportement *passé*. Chaque réponse modèle ci-dessous suit la méthode **STAR**. Les scénarios de leadership technique sont dans [Leadership](leadership-behavioral.md).

### ⭐ La méthode STAR

| Lettre | Partie | Part de la réponse | À dire |
|--------|--------|--------------------|--------|
| **S** | Situation | ~10 % | Contexte en 1–2 phrases : équipe, système, enjeux. |
| **T** | Tâche | ~10 % | *Votre* responsabilité ou objectif — ce dont vous étiez garant. |
| **A** | Action | ~60 % | Ce que **vous** avez fait, étape par étape, et pourquoi. « Je », pas « nous ». |
| **R** | Résultat | ~20 % | Résultat mesurable + ce que vous avez appris / feriez autrement. |

```text
S : « Le p95 de notre API de checkout est monté à 2,4 s pendant la montée en charge du Black Friday. »
T : « Propriétaire du service, j'avais 3 jours pour passer sous 800 ms sans réécriture. »
A : « J'ai profilé avec async-profiler, trouvé un N+1 dans le mapper de commandes, ajouté un fetch join,
      un cache Redis pour la liste de prix et un test de charge en CI contre les régressions. »
R : « Le p95 est passé à 420 ms, aucun incident le jour J, et le test de charge a détecté deux régressions ensuite. »
```

**Règles pratiques**

- Préparez une **banque d'histoires** de 6–8 cas réels (voir l'[aide-mémoire](#cheat-sheet)) ; chacune peut répondre à plusieurs questions.
- **Chiffrez** les résultats (latence, coût, incidents, temps gagné, taille d'équipe).
- Restez à **2 minutes** ; laissez l'interlocuteur creuser.
- Un échec est acceptable — une histoire sans apprentissage ne l'est pas.
- N'inventez jamais : les questions de suivi le révèlent.

### 🟢 Fondamentaux

#### Présentation

#### B1. Parlez-moi de vous. {#yourself}
**Pourquoi on la pose :** voir si vous résumez votre parcours en un récit cohérent et pertinent.

- **S** — Présent : « Je suis ingénieur full-stack senior avec 8 ans d'expérience, surtout des backends Java/Spring Boot et des frontends React sur Kubernetes. »
- **T** — Passé : votre responsabilité dans le dernier poste (ex. propriétaire de la plateforme de paiement pour 5 squads).
- **A** — Jalons : 2–3 réalisations alignées avec le poste (migration vers l'événementiel, mentorat, réduction des astreintes).
- **R** — Futur : pourquoi ce poste est la suite logique.

**Piège :** réciter son CV chronologiquement pendant 5 minutes. Utilisez *présent → passé → futur* en moins de 90 secondes.

#### B2. Parlez-moi d'une réalisation dont vous êtes particulièrement fier. {#achievement-particularly-proud}
**Pourquoi on la pose :** vos valeurs et l'échelle d'impact à laquelle vous opérez.

- **S** — Monolithe legacy, batch de nuit de 7 h qui échouait régulièrement, bloquant les rapports du matin de la finance.
- **T** — Je me suis porté volontaire pour le fiabiliser et passer sous 1 h.
- **A** — Je l'ai découpé en lots idempotents, déplacé les agrégations lourdes vers les window functions PostgreSQL, parallélisé avec des virtual threads, et ajouté métriques et alerte sur le retard.
- **R** — Durée de 7 h à 38 min, échecs de ~3/mois à 0 sur 6 mois, et le pattern a été réutilisé par deux autres équipes.

**Piège :** choisir une réalisation sans résultat mesurable, ou dire « nous » partout et effacer sa propre part.

#### B3. Quels sont vos plus grandes forces et faiblesses ? {#greatest-strengths-weaknesses}
**Pourquoi on la pose :** lucidité et capacité à progresser activement.

- **S** — Force : je découpe les problèmes flous en incréments livrables. Faiblesse : je prenais trop de choses en charge au lieu de déléguer.
- **T** — Illustrer la force par un cas ; montrer une faiblesse *réelle* mais *traitée*.
- **A** — Force : transformer un « accélérer la recherche » vague en 3 étapes mesurables, première livrée en une semaine. Faiblesse : je liste chaque sprint ce que je peux déléguer, je fais du pair avec le responsable et je revois les résultats plutôt que le code ligne à ligne.
- **R** — Latence de recherche −60 % en 3 sprints ; deux collègues possèdent désormais des composants que je maintenais seul.

**Piège :** « je suis perfectionniste » ou une faiblesse disqualifiante pour le poste.

#### B4. Pourquoi voulez-vous travailler chez nous ? {#want-here}
**Pourquoi on la pose :** motivation, recherche faite, adéquation.

- **S** — Ce que vous avez trouvé : produit, blog technique, stack, problèmes d'échelle.
- **T** — Relier cela à ce que vous voulez devenir.
- **A** — Citer 2 éléments précis (ex. « votre passage à Kafka multi-région » et « votre grille d'évolution ») reliés à votre expérience.
- **R** — Dire ce que vous apporterez dans les 6 premiers mois.

**Piège :** éloges génériques (« belle entreprise ») ou ne parler que de salaire/télétravail.

#### B5. Pourquoi voulez-vous travailler dans la santé ? {#want-healthcare}
**Pourquoi on la pose :** une motivation qui résiste aux jours difficiles, et la compréhension des enjeux du domaine (données de patients, disponibilité, confiance).

- **S** — Votre histoire commence par un lien concret et personnel avec la mission (un proche qui a attendu des semaines un rendez-vous, un projet où votre logiciel avait de vrais utilisateurs qui en dépendaient).
- **T** — Expliquer pourquoi *ce* type de problème, pas seulement « une bonne entreprise ».
- **A** — Relier votre expérience au travail : la fiabilité compte davantage quand une panne signifie une consultation manquée, la confidentialité est une contrainte de conception (RGPD, hébergement de données de santé), et l'échelle est réelle (des millions de rendez-vous). Citez ce que vous avez étudié : le produit, le blog technique, la stack.
- **R** — Terminer sur ce que vous voulez apporter et apprendre, par ex. « je veux que mon travail réduise mesurablement le temps d'attente pour se faire soigner ».

**Piège :** des réponses génériques (« belle culture », « innovant ») ou une flatterie valable pour n'importe quelle entreprise. Autre piège : ignorer les contraintes ; montrer de l'enthousiasme sans reconnaître conformité et sensibilité des données paraît naïf.

*Voir aussi :* [Security Q19](security.md#design-protection-sensitive-healthcare-data) pour ce que protéger des données de santé signifie techniquement, et [Comportemental B4](leadership-behavioral.md#want-here) pour la version générique de cette question.

### 🟡 Pièges seniors

#### Échec et feedback

#### B6. Parlez-moi d'une erreur importante que vous avez commise. {#time-made-significant-mistake}
**Pourquoi on la pose :** responsabilité, honnêteté, et capacité à transformer l'erreur en amélioration systémique.

- **S** — J'ai livré une migration Flyway ajoutant une colonne `NOT NULL` avec valeur par défaut sur une table de 200 M de lignes ; elle a bloqué les écritures 9 minutes en production.
- **T** — En tant qu'auteur, j'ai pris l'incident en charge : rétablir le service, puis empêcher la récidive.
- **A** — Rollback, point de situation toutes les 10 minutes, postmortem sans blâme, puis checklist de migration (patterns online-safe, `CONCURRENTLY`, backfill par lots) et job CI qui rejoue les migrations sur un snapshot de taille production.
- **R** — Incident clos en 9 min ; aucun incident lié aux migrations durant 12 mois, et le check CI a bloqué 3 migrations dangereuses d'autres équipes.

**Piège :** un faux échec (« je travaille trop ») ou accuser les autres/les outils. Assumez dès la première phrase.

#### B7. Parlez-moi d'un feedback difficile reçu. Comment avez-vous réagi ? {#time-received-tough-feedback-react}
**Pourquoi on la pose :** réceptivité et ego.

- **S** — Mon tech lead m'a dit que mes PR étaient trop grosses et difficiles à relire, ralentissant l'équipe.
- **T** — Changer ma façon de travailler sans perdre en vitesse de livraison.
- **A** — J'ai demandé des exemples concrets, adopté des PR empilées de moins de 400 lignes, ajouté un template de description (contexte, risque, plan de test) et demandé un point de suivi après un mois.
- **R** — Délai moyen de relecture de 2 jours à 5 heures ; le lead m'a ensuite demandé de partager l'approche avec l'équipe.

**Piège :** se défendre, ou choisir un « feedback » qui est en fait un compliment déguisé.

#### Conflit et influence

#### B8. Décrivez un conflit avec un collègue et comment vous l'avez résolu. {#conflict-colleague-resolved}
**Pourquoi on la pose :** intelligence émotionnelle ; escaladez-vous, évitez-vous, ou résolvez-vous ?

- **S** — Un collègue backend et moi divergions sur le versionnement d'API : il voulait des changements cassants en `v1`, j'avais besoin de stabilité pour l'app mobile.
- **T** — Décider vite sans abîmer la relation.
- **A** — J'ai proposé un appel de 30 min, reformulé d'abord ses contraintes (pression de livraison), puis montré les données d'adoption mobile (35 % des utilisateurs sur d'anciennes versions). Nous avons convenu de changements additifs plus une fenêtre de dépréciation, consignés dans un ADR.
- **R** — Pas de mise à jour forcée de l'app, fonctionnalité livrée à temps, et le template d'ADR réutilisé pour d'autres décisions d'API.

**Piège :** une histoire où vous aviez simplement raison. Montrez de l'empathie et un compromis fondé sur des données.

#### B9. Parlez-moi d'une fois où vous étiez en désaccord avec votre manager. {#time-disagreed-manager}
**Pourquoi on la pose :** exprimez-vous votre avis avec respect, et vous engagez-vous une fois la décision prise ?

- **S** — Mon manager voulait livrer une fonctionnalité sans test de charge pour tenir la date d'une démo client.
- **T** — Exposer le risque sans bloquer l'objectif business.
- **A** — J'ai estimé le coût d'un échec (démo à 10× le trafic habituel), proposé un test de charge réduit d'1 jour sur le chemin critique, et offert de retirer un écran non essentiel pour le financer.
- **R** — Le test a révélé une limite de pool de connexions qui aurait fait planter la démo ; corrigée en 2 heures. Mon manager demande désormais le même « test minimum viable » sur les deadlines.

**Piège :** « disagree and commit » sans montrer le désaccord, ou à l'inverse refuser de s'engager ensuite.

*Méthode :* [Leadership Q3](leadership-behavioral.md#push-back-technical-decision-coming) traite de la façon de contester un interlocuteur senior ; cette question demande l'histoire.

#### B10. Parlez-moi d'une fois où vous avez travaillé sous forte pression ou avec une deadline serrée. {#time-worked-under-tight-deadline}
**Pourquoi on la pose :** priorisation et sang-froid.

- **S** — Un changement réglementaire exigeait un nouveau parcours KYC en 3 semaines ; l'estimation était de 6.
- **T** — Tech lead, livrer le minimum conforme à temps.
- **A** — J'ai séparé le périmètre en *obligatoire* (légal) et *souhaitable*, obtenu l'accord produit, mis le reste derrière des feature flags, instauré un point quotidien de 15 min et réduit la latence de relecture par du pair sur les parties risquées.
- **R** — Livré en 19 jours avec 0 bug critique ; le reste est arrivé au sprint suivant.

**Piège :** les exploits héroïques (nuits blanches) comme action principale. Un senior réduit le périmètre et le risque.

#### B11. Parlez-moi d'une fois où le besoin était flou ou changeant. {#time-had-unclear-changing-requirement}
**Pourquoi on la pose :** aisance face à l'ambiguïté.

- **S** — Le produit demandait « un meilleur tableau de bord de reporting » sans définir « meilleur ».
- **T** — Transformer l'ambiguïté en périmètre clair et testable.
- **A** — J'ai interrogé 5 utilisateurs, prototypé 2 maquettes en une journée, fixé 3 métriques de succès (temps pour trouver un rapport, usage de l'export, tickets support) et livré un MVP derrière un flag.
- **R** — Tickets support sur les rapports −40 % ; deux demandes « indispensables » se sont révélées inutiles, soit ~3 semaines économisées.

**Piège :** attendre des exigences parfaites, ou développer beaucoup avant de valider.

### 🔴 Expert / Ouvert

#### B12. Parlez-moi d'une fois où vous avez influencé une décision sans autorité hiérarchique. {#time-influenced-decision-having-authority}
**Pourquoi on la pose :** impact de niveau staff, inter-équipes.

- **S** — Quatre équipes utilisaient quatre formats de logs différents, rendant le traçage inter-services pénible en incident.
- **T** — Standardiser sans être le manager de personne.
- **A** — J'ai mesuré la douleur (MTTR des 5 derniers incidents), rédigé une RFC courte avec un prototype fonctionnel (OpenTelemetry + un starter Spring partagé), présenté à chaque lead, et proposé de faire la PR de migration pour les deux premières équipes.
- **R** — 4/4 équipes l'ont adopté en un trimestre ; le MTTR des incidents inter-services est passé de ~70 à ~25 min.

**Piège :** « je les ai convaincus » sans mécanisme. Montrez données, prototype et coût d'adoption réduit.

*Méthode :* [Leadership Q3](leadership-behavioral.md#push-back-technical-decision-coming) traite de l'influence sans autorité ; cette question demande l'histoire.

#### B13. Parlez-moi d'un changement technique majeur que vous avez piloté. {#time-drove-major-technical-change}
**Pourquoi on la pose :** vision, gestion du risque et exécution à grande échelle.

- **S** — Un monolithe déployé une fois par mois, avec 1 release sur 4 annulée.
- **T** — Mener le passage à des services déployables indépendamment et à un CI/CD, avec une petite équipe.
- **A** — Pattern strangler, extraction d'abord du module le plus modifié, tests de contrat et canary releases, démos hebdomadaires aux parties prenantes, décisions consignées en ADR.
- **R** — Fréquence de déploiement de mensuelle à quotidienne pour le service extrait, taux de rollback de 25 % à <5 %, et la feuille de route a été reprise pour 3 modules de plus.

**Piège :** une histoire de réécriture big-bang ; on attend des étapes incrémentales et réversibles.

#### B14. Parlez-moi d'une fois où vous avez amélioré la qualité du code dans votre équipe. {#time-improved-code-quality-team}
**Pourquoi on la pose :** voir si vous relevez le niveau par l'influence et les habitudes plutôt que par des leçons ou de l'héroïsme.

- **S** — Notre service avait des tests instables, des revues de 40 minutes et une classe de régressions récurrente autour de la gestion des dates.
- **T** — Améliorer la qualité de façon mesurable sans geler les fonctionnalités ni blâmer personne.
- **A** — J'ai d'abord mesuré (taux de tests instables, bugs échappés, durée de revue), proposé deux petits changements acceptés par l'équipe (un modèle de PR avec une checklist de tests, un utilitaire de dates partagé et testé), automatisé ce qui pouvait l'être (analyse statique et formateur en CI pour que les revues portent sur la conception), mis en quarantaine les tests instables avec un responsable et une échéance, et tenu une « revue de bugs » mensuelle de 30 minutes pour apprendre des échappements.
- **R** — Les tests instables sont passés de 12 % à moins de 2 %, la durée médiane de revue est tombée à 15 minutes, et les régressions liées aux dates ont cessé pendant deux trimestres. Les pratiques ont survécu à mon implication.

**Piège :** une croisade en solo (« j'ai tout réécrit ») ou une réponse vague sans chiffres. Des améliorations que l'équipe n'a pas adoptées ne sont pas une réussite.

*Voir aussi :* [Testing Q18](testing.md#load-test-rest-api-gatling) pour les contrôles qualité dans le pipeline, et [Comportemental B20](leadership-behavioral.md#time-had-balance-quality-against) sur qualité contre vitesse.

#### B15. Parlez-moi d'une fois où vous avez accompagné un collègue en difficulté. {#time-mentored-helped-struggling-teammate}
**Pourquoi on la pose :** effet multiplicateur et patience.

- **S** — Un développeur junior dépassait ses estimations d'un facteur 2 depuis deux sprints et perdait confiance.
- **T** — L'aider à devenir autonome sans prendre ses tâches.
- **A** — Pair deux fois par semaine, apprentissage du découpage en tâches ≤1 jour, point quotidien, et feedback sur *sa façon d'investiguer* plutôt que de corriger le code à sa place.
- **R** — Estimations à ±20 % après 6 semaines, et première astreinte en autonomie au mois 3.

**Piège :** se présenter en héros qui a tout réglé. Le résultat doit être *leur* progression.

*Méthode :* [Leadership Q1](leadership-behavioral.md#technical-feedback-mentorship-effective-opposed) et [Leadership S2](leadership-behavioral.md#junior-engineer-prs-keep-repeating) traitent du mentorat efficace ; cette question demande l'histoire.

#### B16. Parlez-moi d'une décision prise avec des informations incomplètes. {#decision-made-incomplete-information}
**Pourquoi on la pose :** jugement sous incertitude et réversibilité.

- **S** — Il fallait choisir un broker de messages en 2 semaines, avec des prévisions de débit floues.
- **T** — Décider sans sur-investir ni enfermer l'entreprise.
- **A** — J'ai classé la décision comme *réversible avec un coût*, mené un spike de 3 jours Kafka vs RabbitMQ avec un profil de charge réaliste, masqué le broker derrière une interface, et rédigé un ADR avec des déclencheurs de réexamen explicites.
- **R** — Kafka retenu ; 8 mois plus tard le volume était 5× la prévision sans aucun changement nécessaire. Le déclencheur d'ADR n'a jamais été atteint.

**Piège :** feindre la certitude. Montrez comment vous avez réduit l'incertitude et limité le rayon d'impact.

#### B17. Parlez-moi d'une fois où vous vous êtes assuré que votre travail apportait une vraie valeur aux utilisateurs. {#time-made-sure-delivered-real}
**Pourquoi on la pose :** voir si vous vous souciez des résultats, pas seulement des tickets livrés.

- **S** — On nous a demandé un export en libre-service pour les administrateurs de cabinets ; le cahier des charges décrivait un module de reporting complet.
- **T** — Livrer ce dont les utilisateurs avaient réellement besoin, tôt, et prouver que ça fonctionnait.
- **A** — J'ai parlé à trois administrateurs avant de construire et constaté que 90 % du besoin était un CSV mensuel. Nous l'avons livré en une semaine derrière un feature flag, instrumenté l'usage (exports par semaine, échecs, temps de réalisation) et itéré à partir des données plutôt que de la spec initiale.
- **R** — Les tickets de support sur le sujet ont baissé de 60 %, l'adoption a atteint 70 % des cabinets en un mois, et nous avons évité deux mois de reporting que personne n'aurait utilisé.

**Piège :** décrire la livraison (« nous avons livré à temps ») sans preuve d'impact. Dites comment vous avez mesuré la valeur, et ce que vous avez choisi de *ne pas* construire.

*Voir aussi :* [Full Stack Q8](fullstack-devops-k8s.md#p50-p95-p99-latency-average) sur la mesure de ce que vivent les utilisateurs.

#### B18. Parlez-moi d'un incident de production que vous avez investigué. {#production-incident-investigated}
**Pourquoi on la pose :** calme, méthode et apprentissage sous pression, plus l'honnêteté sur votre part de responsabilité.

- **S** — Des alertes de latence se sont déclenchées sur l'API de réservation à 14h10 et le taux d'erreurs est monté à 8 %.
- **T** — Rétablir le service d'abord, puis trouver la cause racine, comme responsable de l'incident.
- **A** — J'ai déclaré l'incident et réparti les rôles (une personne communique, une investigue). J'ai regardé ce qui avait changé (un déploiement 20 minutes plus tôt) et fait un rollback, ce qui a rétabli le service en 12 minutes. Puis, avec métriques, logs et traces côte à côte, j'ai trouvé une nouvelle requête sans index qui épuisait le pool de connexions. J'ai rédigé un post-mortem sans blâme : chronologie, cause racine, facteurs contributifs (pas de test de charge, pas de contrôle du plan d'exécution en revue) et actions avec responsables.
- **R** — Ajout d'un contrôle de requêtes lentes dans le pipeline et d'une alerte de saturation du pool ; aucune récidive l'année suivante, et le délai moyen de détection est passé de 9 à 2 minutes.

**Piège :** un récit héroïque, accuser une personne, ou inverser l'ordre atténuation puis diagnostic. Montrez la séquence : stabiliser, diagnostiquer, prévenir.

*Voir aussi :* [Leadership S6](leadership-behavioral.md#production-incident-traces-back-architectural) pour un incident causé par votre propre décision, et [Full Stack Q36](fullstack-devops-k8s.md#reducing-endpoint-p95-latency-9) pour une méthode d'investigation de latence.

#### B19. Parlez-moi d'une fois où vous avez changé une décision technique face à de nouveaux éléments. {#time-changed-technical-decision-after}
**Pourquoi on la pose :** honnêteté intellectuelle et capacité à changer de cap sans ego.

- **S** — J'avais proposé de mettre en cache les disponibilités pendant 10 minutes pour réduire la charge de la base, et l'équipe avait approuvé.
- **T** — Vérifier si la décision tenait toujours une fois les données d'usage réelles disponibles.
- **A** — Après la mise en production, les métriques ont montré un taux de succès du cache de seulement 35 % et que des créneaux périmés provoquaient des tentatives de double réservation (hausse des erreurs de conflit). J'ai présenté les données à l'équipe sans défendre mon idée initiale, proposé un TTL plus court de 30 secondes avec invalidation à la réservation, et fait tourner les deux variantes derrière un flag pendant une semaine.
- **R** — Les erreurs de conflit ont baissé de 90 %, le taux de succès est monté à 80 % et la charge de la base a tout de même diminué de 40 %. L'équipe m'a ensuite demandé d'inscrire l'étape « décider, mesurer, réexaminer » dans notre modèle de conception.

**Piège :** choisir un exemple anodin, ou un cas où vous aviez « raison depuis le début ». Montrez quel élément vous a fait changer d'avis, comment vous l'avez dit publiquement, et comment vous avez limité le coût du revirement.

*Voir aussi :* [Comportemental B16](leadership-behavioral.md#decision-made-incomplete-information) sur la décision avec des informations incomplètes.

#### B20. Parlez-moi d'un arbitrage entre qualité et rapidité. {#time-had-balance-quality-against}
**Pourquoi on la pose :** pragmatisme et intégrité.

- **S** — Un contrat commercial dépendait d'une fonctionnalité en 2 semaines ; la conception propre en demandait 5.
- **T** — Livrer vite sans créer une dette ingérable.
- **A** — J'ai proposé une tranche verticale fine avec les parties risquées (argent, permissions) entièrement testées et le reste simplifié, consigné les raccourcis en tickets avec responsable et date, et négocié un créneau de refactoring au sprint suivant.
- **R** — Contrat signé à temps ; tickets de dette clos en 3 semaines, évitant deux bugs de production qui auraient sinon été livrés.

**Piège :** « nous ne faisons jamais de compromis » (irréaliste) ou « livré et oublié » (irresponsable).

### 📞 Entretien avec le recruteur

Ces questions arrivent lors du premier appel de 20 minutes, en général avec un recruteur plutôt qu'un ingénieur. Ce ne sont pas des histoires STAR : répondez en 30–60 secondes, restez positif, et préparez la formulation à l'avance.

#### B21. Pourquoi quittez-vous votre poste actuel ? {#leaving-current-job}
**Pourquoi on la pose :** pour détecter un conflit, un problème de performance ou une suite de passages courts.

- **Présentez-le comme un mouvement vers quelque chose :** « Je veux porter des décisions d'architecture entre équipes, et ce rôle n'existe pas là où je suis. »
- **Un fait, pas de grief :** réorganisation, fin d'un projet, une direction technique que vous ne partagez pas.
- **Faites le lien avec ce poste :** ce que ce poste offre qui y correspond.

**Piège :** critiquer votre manager ou votre entreprise. Même si c'est vrai, l'interlocuteur entend « cette personne dira la même chose de nous ».

#### B22. Quelles sont vos prétentions salariales ? {#salary-expectations}
**Pourquoi on la pose :** pour vérifier que vous entrez dans le budget avant d'investir du temps d'entretien.

- **Renseignez-vous d'abord :** données de marché pour le poste, le niveau et la ville (études de salaires, pairs, levels.fyi).
- **Donnez une fourchette ancrée sur la rémunération totale :** « Vu le périmètre et le marché, je vise 75–85 k€ de fixe, selon le package global. » Placez votre cible dans la moitié basse de la fourchette.
- **Ou différez poliment une fois :** « J'aimerais d'abord comprendre le périmètre. Quel est le budget du poste ? » S'ils insistent, donnez la fourchette.

**Piège :** donner un chiffre sans recherche, ou votre salaire actuel comme ancrage. Dans certains pays, l'employeur n'a pas le droit de demander votre salaire actuel.

#### B23. Où vous voyez-vous dans trois à cinq ans ? {#see-yourself-three-five-years}
**Pourquoi on la pose :** pour vérifier votre ambition et si elle correspond au parcours qu'ils peuvent offrir.

- **Nommez une direction, pas un titre :** « Porter la direction technique d'un domaine produit : architecture, mentorat, livraison. »
- **Montrez le lien :** quelles compétences ce poste construit dans ce sens.
- **Restez ouvert :** filière experte (staff engineer) ou management, selon là où vous apportez le plus.

**Piège :** « à votre place » ou « à la tête de ma propre startup ». Les deux suggèrent que vous partirez ou ferez concurrence.

#### B24. Présentez-moi en profondeur technique un projet dont vous êtes fier. {#project-re-proud-technical-depth}
**Pourquoi on la pose :** c'est l'approfondissement que les recruteurs de postes de tech lead confient aux ingénieurs ; on teste une vraie appropriation et la compréhension des compromis derrière les décisions.

- **Contexte en 2 phrases :** problème métier, échelle (utilisateurs, requêtes/s, volume de données), taille de l'équipe.
- **Esquisse d'architecture :** composants principaux et flux de données. Soyez prêt à la dessiner.
- **Vos décisions :** deux ou trois choix que vous avez faits, les alternatives, et pourquoi (cohérence, coût, compétences de l'équipe).
- **Ce qui a mal tourné et ce que vous changeriez :** c'est là que la séniorité se voit.
- **Résultat chiffré :** latence, coût, incidents, vitesse de livraison.

**Piège :** décrire ce que « l'équipe » a construit sans dire quelles décisions étaient les vôtres, ou ne pas savoir répondre à « pourquoi pas X ? ».

#### B25. Pourquoi un poste de tech lead, et que fait un tech lead selon vous ? {#tech-lead-role-tech-lead}
**Pourquoi on la pose :** pour vérifier que vous savez que le poste consiste à démultiplier l'équipe, pas à être le meilleur codeur.

- **Définition :** responsable de la direction technique et de la livraison d'une équipe : décisions d'architecture, niveau d'exigence, déblocage, mentorat, et traduction entre produit et ingénierie.
- **Preuves :** les fois où vous en avez déjà assuré une partie (animé une revue de conception, intégré des personnes, piloté des incidents).
- **Équilibre :** combien vous codez encore (souvent 30–50 %) et ce que vous délégueriez.

**Piège :** « Je veux décider de l'architecture ». La réponse doit porter sur les résultats de l'équipe, pas sur votre contrôle. Voir [Leadership](leadership-behavioral.md) pour les questions de méthode.

#### B26. Avez-vous des questions pour nous ? {#have-any-questions}
**Pourquoi on la pose :** pour mesurer votre intérêt et votre jugement. « Non » est un signal faible.

- **Sur l'équipe :** « Comment l'équipe se répartit-elle entre produit, maintenance et astreinte ? »
- **Sur les pratiques :** « Comment le code arrive-t-il en production, et à quelle fréquence ? » « Que s'est-il passé lors de votre dernier incident ? »
- **Sur le poste :** « À quoi ressemblerait la réussite dans ce poste après six mois ? »
- **Sur le processus :** « Quelles sont les prochaines étapes, et y a-t-il un point de mon profil que vous aimeriez que je clarifie ? »

**Piège :** ne poser que des questions sur le télétravail et les avantages au premier appel, ou des questions dont la réponse est sur la page carrières.

#### B27. Pourquoi notre entreprise ? {#our-company}
**Pourquoi on la pose :** pour distinguer un intérêt réel pour leur produit et leur ingénierie d'une réponse générique sur la santé ([B5](leadership-behavioral.md#want-healthcare)).

- **S** — Partir du produit en tant qu'utilisateur : vous ou un proche avez réservé avec, ou vous savez comment les praticiens utilisent l'agenda, la téléconsultation ou le partage de documents.
- **T** — Nommer les problèmes d'ingénierie qui vous attirent : une réservation à fort trafic sans aucune tolérance pour la double réservation, la sécurité et la conformité des données de santé dans plusieurs pays, et une grande base de code qui continue de livrer souvent.
- **A** — Les relier à votre expérience par un ou deux exemples concrets (un service Java/Spring que vous avez fait passer à l'échelle, une fonctionnalité React utilisée par des milliers de personnes, un incident que vous avez mené), et citer ce que vous avez lu sur leur ingénierie (articles de blog, conférences, open source, stack).
- **R** — Terminer sur l'impact que vous voulez avoir dans l'équipe pour laquelle vous passez l'entretien, dans leurs termes : les patients trouvent un soin plus vite, les praticiens passent moins de temps sur l'administratif.

**Piège :** réciter la page carrières ou énumérer les avantages. Vérifiez les faits que vous citez, et si vous ne savez pas quelque chose de leur stack, dites ce que vous aimeriez apprendre plutôt que de deviner.

#### B28. Parlez-moi d'une fonctionnalité que vous avez livrée de bout en bout avec le produit et le design. {#feature-delivered-end-end-product}
**Pourquoi on la pose :** on attend d'un product engineer fullstack qu'il porte un problème, pas seulement des tickets : challenger le périmètre, livrer par petites étapes et mesurer le résultat.

- **S** — Le problème utilisateur et comment vous saviez que c'en était un (données, tickets de support, entretiens utilisateurs).
- **T** — Votre rôle sur le backend, le frontend et le déploiement, et la contrainte (échéance, legacy, conformité).
- **A** — Comment vous avez façonné la solution avec le PM et le designer (ce que vous avez proposé, coupé ou simplifié), les choix techniques (API, modèle de données, feature flag, migration), et comment vous l'avez livrée progressivement (utilisateurs internes, déploiement par pourcentage).
- **R** — Le résultat mesuré (adoption, conversion, temps gagné, moins de tickets de support) et ce que vous avez changé après avoir vu les données.

**Piège :** une histoire purement technique sans utilisateur ni métrique, ou « le PM a tout décidé ». Montrez que vous avez influencé le *quoi*, pas seulement le *comment*.

## 🎤 Quiz oral

Dix questions réparties sur les niveaux. Répondez à chacune **à voix haute en 2–3 minutes**, sans regarder, en structurant : contexte → options → décision → compromis. Ouvrez ensuite la question et notez-vous : **0** vide · **1** définition seule · **2** plus un exemple · **3** plus compromis et piège. Sous 24/30, refaites les points faibles après deux semaines. Les questions et scénarios sont dans les sections ci-dessus.

1. Q1. Qu'est-ce qui rend le feedback technique et le mentorat réellement efficaces, et pas seulement corrects ?
2. Q2. Un ingénieur junior commet sans cesse la même catégorie d'erreur malgré des commentaires de code review répétés. Quelle est votre approche concrète ?
3. Q3. Comment contestez-vous une décision technique venant d'une partie prenante senior ou d'un manager que vous jugez erronée ?
4. Q4. En tant que tech lead, comment gérez-vous une design review où deux ingénieurs seniors sont fortement en désaccord ?
5. Q5. Comment cadrez-vous et estimez-vous un projet à très forte incertitude pour des parties prenantes qui veulent une date ferme ?
6. Q6. Vous héritez d'une équipe au moral bas et avec une dette technique importante. Décrivez votre approche pour les 90 premiers jours en tant que tech lead.
7. Q7. Comment décidez-vous entre construire un composant vous-même et l'acheter (ou adopter de l'open source) ?
8. S1. Une design review entre deux ingénieurs seniors bloque un projet pendant des semaines sans résolution
9. S4. Une partie prenante exige une deadline irréaliste pour une fonctionnalité complexe
10. S6. Un incident de production remonte à une décision d'architecture que vous avez personnellement prise

Q8–Q13 (coordination d'incident, RFC/ADR, recrutement, délégation, onboarding, manage up) sont de bons tours supplémentaires.

### Tour comportemental

Choisissez 5 questions, répondez à chacune **à voix haute en moins de 2 minutes** en suivant S → T → A → R. Notez-vous : **0** digression · **1** histoire sans résultat · **2** STAR clair · **3** STAR avec chiffres et apprentissage. Sous 12/15, réécrivez les histoires de votre banque.

1. B5. Pourquoi voulez-vous travailler dans la santé ?
2. B6. Une erreur importante.
3. B8. Un conflit avec un collègue.
4. B12. Influencer sans autorité.
5. B16. Une décision avec informations incomplètes.

## 📌 Cheat-sheet {#cheat-sheet}

### Leadership au quotidien

> **À retenir d'abord :** (1) feedback = spécifique, opportun, avec le pourquoi ; (2) discuter l'idée, pas la personne ; (3) assumer ses erreurs simplement ; (4) dire à voix haute compromis et incertitudes ; (5) mauvaises nouvelles tôt, avec un plan.

- **Feedback** — spécifique, opportun, et qui explique le *pourquoi*. *« Ta PR n'avait pas de tests pour le chemin de retry » vaut mieux que « fais plus attention ».*
- **Design reviews** — séparer les personnes des désaccords. *Débattre du design, pas de son auteur.*
- **Postmortems blameless** — assumer ses erreurs simplement. *Blameless = chercher les causes système, pas un coupable.*
- **Compromis et estimations** — les rendre explicites plutôt qu'implicites, surtout les estimations sous incertitude. *Exemple : « 2–4 semaines ; l'inconnue est l'API du fournisseur ».*
- **Déléguer** — déléguer des résultats (pas des tâches) avec points de contrôle.
- **Dire non** — non = compromis + alternative. *Exemple : « Pas ce sprint, mais on peut faire une version réduite. »*
- **Onboarder** — viser un changement en prod dès la semaine 1. *Un petit changement réel donne confiance et révèle les lacunes de setup.*
- **Manage up** — mauvaises nouvelles tôt, avec un plan.
- **Performance en baisse** — trouver *ce qui a changé* avant de supposer un problème de performance. *Ensuite : attentes écrites claires, soutien, objectifs mesurables, et un processus formel seulement si nécessaire.*

### Décisions et stratégie technique

> **À retenir d'abord :** (1) construire ce qui différencie, acheter les commodités ; (2) consigner les décisions en ADR ; (3) traduire la dette technique en coût métier ; (4) toute RFC propose 2+ options.

- **Build vs buy** — construire les différenciateurs, acheter les commodités. *Comparer le TCO (coût total de possession) à 10× l'échelle, en incluant le lock-in et le coût de sortie.*
- **Isoler les fournisseurs** — derrière un adapter (une fine interface que l'on possède). *Changer de fournisseur ne touche alors qu'un seul endroit.*
- **ADR** (Architecture Decision Record) — consigner la décision avec une date de revue. *Les futurs lecteurs apprennent pourquoi, pas seulement quoi.*
- **Négociation de la dette technique** — traduire la dette en coût du retard, incidents et éléments de roadmap bloqués. *Les gens produit réagissent au coût, pas à « le code est moche ».*
- **Livraison de la dette technique** — refactorer le long de la roadmap et réserver une part fixe de capacité (ex. 20 % de chaque sprint).
- **Contenu RFC/ADR** — problème, 2+ options avec coûts, recommandation, décideur et échéance. *RFC = Request For Comments, une proposition écrite soumise à retours.*

### Incidents et santé de l'équipe

> **À retenir d'abord :** (1) assigner commander / intervenants / comms ; (2) atténuer avant de diagnostiquer ; (3) points à cadence fixe ; (4) ne paginer que sur les alertes actionnables.

- **Coordination d'incident** — séparer les rôles : commander (décide), intervenants (corrigent), comms (informent les parties prenantes). *Une seule personne pour les trois finit par perdre quelque chose.*
- **Atténuer avant de diagnostiquer** — d'abord stopper l'hémorragie (rollback, failover), chercher la cause racine ensuite.
- **Points à cadence fixe** — ex. toutes les 30 minutes, même « sans nouvelle ». *Évite que l'on interrompe les intervenants.*
- **Fatigue d'alertes d'astreinte** — un faible ratio de pages actionnables (peu de pages exigent une vraie action) désensibilise une équipe ; ce n'est pas un problème de discipline. *Ajuster les seuils et dédupliquer selon l'actionnabilité réelle, pas le risque théorique.*

### Recrutement

> **À retenir d'abord :** définir les signaux d'avance, noter avec une grille, écrire les retours avant le débrief.

- **Recrutement** — signaux définis d'avance, grille, retours écrits avant le débrief. *Écrire d'abord évite de se laisser influencer par la voix la plus forte de la salle.*

### Comportemental (STAR)

#### Construire sa réponse

- **STAR** — une structure d'histoire en 4 parties : Situation (10 %) · Tâche (10 %) · Action (60 %) · Résultat (20 %). *Dire « je », pas « nous », et mettre des chiffres dans le résultat.*
- **Banque d'histoires (préparer 6–8)** — à avoir sous la main : un incident géré · un échec · un conflit · un gros changement technique · un cas de mentorat · une deadline serrée · un désaccord avec un manager · un projet ambigu.
- **Réutilisation** — une histoire répond à plusieurs questions. *Changer l'angle : ce que vous avez *fait* vs ce que vous avez *appris*.*

#### Types de questions courants

- **Réponses sur un échec** — assumer dès la première phrase → correction → prévention systémique (un changement pour que ça ne puisse plus arriver) → suites mesurables.
- **Réponses sur un conflit** — comprendre sa contrainte → s'appuyer sur des données → compromis → préserver la relation.
- **Terminer par l'apprentissage** — finir par « Ce que je ferais différemment, c'est… ».

#### Entretien avec le recruteur

- **Court et positif** — 30–60 secondes, en allant *vers* quelque chose, jamais contre votre employeur.
- **Salaire** — fourchette documentée sur la rémunération totale, cible dans la moitié basse.
- **Approfondissement de projet** — contexte, esquisse d'architecture, *vos* décisions et alternatives, ce que vous changeriez, chiffres.
- **Questions à poser** — répartition de l'équipe, chemin vers la production, dernier incident, réussite à six mois.

#### À éviter

- **Signaux d'alerte** — accuser les autres, aucun résultat, tout en héroïsme, fausses faiblesses, longs monologues chronologiques.
- **Pourquoi la santé** — une raison concrète, personnelle ou professionnelle, reliée à l'impact sur patients/praticiens et à ce que vous pouvez y construire. *Évitez le générique « j'aime aider les gens ».*

### Banque d'histoires STAR {#banque-histoires-star}

Prépare six histoires réelles ; chacune répond à plusieurs questions. Remplis Situation, Tâche, Action, Résultat (avec un chiffre défendable) pour chacune.

| Histoire | Contenu type | Répond à |
|----------|--------------|----------|
| 1. Réalisation fière | Une livraison à impact mesurable | [B2](#achievement-particularly-proud), [B13](#time-drove-major-technical-change), [B17](#time-made-sure-delivered-real), [B24](#project-re-proud-technical-depth) |
| 2. Erreur ou incident | Assumer la cause, montrer la correction et la leçon | [B6](#time-made-significant-mistake), [B18](#production-incident-investigated), [B19](#time-changed-technical-decision-after) |
| 3. Conflit ou désaccord | Faits, écoute, issue | [B8](#conflict-colleague-resolved), [B9](#time-disagreed-manager), [B12](#time-influenced-decision-having-authority) |
| 4. Pression et arbitrages | Deadline, qualité vs vitesse, informations incomplètes | [B10](#time-worked-under-tight-deadline), [B16](#decision-made-incomplete-information), [B20](#time-had-balance-quality-against) |
| 5. Mentorat et qualité | Accompagner un collègue, améliorer la qualité du code | [B14](#time-improved-code-quality-team), [B15](#time-mentored-helped-struggling-teammate), [B7](#time-received-tough-feedback-react) |
| 6. Ambiguïté et motivation | Besoins flous, pourquoi ce poste ou la santé | [B11](#time-had-unclear-changing-requirement), [B4](#want-here), [B5](#want-healthcare), [B25](#tech-lead-role-tech-lead) |
