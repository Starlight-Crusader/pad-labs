## Microservice-based Chess Website

### Application Suitability Assessment
1. Chess websites may experience different levels of traffic in different parts of the system, for example during tournaments, live broadcasts, or when new features are released. Microservices allow **to independently scale** high-load services without affecting other parts of the system.*
2. Microservices enable working on independent features or services without stepping on each other’s toes. It becomes possible **to update or deploy individual services** without redeploying the entire application.
* e.g., *Chess.com* separates its puzzle generator, allowing a dedicated team to work on improving it, deploy new algorithms, or fix bugs without disrupting other critical services like matchmaking or game analysis.

### Service Boundaries
![Architecture](./architecture.png)
* Service A handles everything regarding the **user data**: authentication, friend system, rating
* Service B handles everything related to the **games played** on the website: lobbies (including spectators), moves recording; also requests rating updates and new friend requests from A

### Technology Stack and Communication Patterns
* Service A (**JS**): **Express** + **MongoDB** (a common combination)
* Service B (**Python**): **Django** + **PostgreSQL** (a common combination) + **Dj Channels** (WS) + **Redis** (Channels storage)
* API Gateway (**Go**): **Fiber**
* Inter-service communication: RESTful APIs

### Data Management Design
* Service A endpoints:

      /api/users/auth/signup - creates a new account
      /api/users/auth/signin - logs into an existing account
      /api/users/friends/search?uname= - searches users by username
      /api/users/friends/req/<int:id> - creates a friend request
      /api/users/friends/get - gets all existing friend requests
      /api/users/friends/add?id=&accepted= - resolves a friend request
      /api/users/ratings/upd?id=&del= - updates user's rating

* Service B endpoints:

      /api/records/save - saves a record of moves
      /api/records/get-all - gets all the records' id-s and datetime data
      /api/records/get/<int:id> - get an actuall record by id
      /api/games/create - creates a new lobby
      /api/games/discover - gets a list of lobbies to join (filtered by rating)
      wss://.../api/games/wss/lobby/<int:id> - lobby consumer (removed on empty)

### Deployment & Scaling
Usage of Docker, Docker Compose, Kubernetes, and stuff