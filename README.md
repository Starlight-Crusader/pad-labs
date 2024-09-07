## Microservice-based Chess Website

### Application Suitability Assessment
1. Chess websites may experience different levels of traffic in different parts of the system, for example during tournaments, live broadcasts, or when new features are released. Microservices allow **to independently scale** high-load services without affecting other parts of the system.*
2. Microservices enable working on independent features or services without stepping on each other’s toes. It becomes possible **to update or deploy individual services** without redeploying the entire application.
* e.g., *Chess.com* separates its puzzle generator, allowing a dedicated team to work on improving it, deploy new algorithms, or fix bugs without disrupting other critical services like matchmaking or game analysis.

### Service Boundaries (architecture.png)
* Service A handles everything regarding the **user data**: authentication, friend system, rating
* Service B handles everything related to the **games played** on the website: lobbies (including spectators), moves recording

### Technology Stack and Communication Patterns
* Service A: **Express** + **MongoDB**
* Service B: **Django** + **PostgreSQL** + **Dj Channels** (WS) + **Redis** (Channels storage)
* API Gateway: Express
* Inter-service communication: RESTful APIs

### Data Management Design
* Service A endpoints:

      /api/users/auth/signup - creates a new account
      /api/users/auth/signin - logs into an existing account
      /api/users/friends/search?uname= - searches users by username
      /api/users/friends/req/<int:id> - creates a friend request
      /api/users/friends/get - gets all existing friend requests
      /api/users/friends/add/<int:id> - accepts a friend request
      /api/users/ratings/upd?id=&del= - updates user's rating

* Service B endpoints:

      /api/records/save - saves a record of moves
      /api/records/get-all - gets all the records' id-s and datetime data
      /api/records/get/<int:id> - get an actuall record by id
      /api/games/create - creates a new lobby
      /api/games/discover - gets a list of lobbies to join (filtered by rating)
      wss://chess.md/api/games/wss/lobby/<int:id>/ - connect to a lobby

### Deployment & Scaling
Usage of Docker, DCompose, Kubernetes, and stuff