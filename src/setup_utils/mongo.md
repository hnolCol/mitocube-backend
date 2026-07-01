# MongoDB Setup with Docker

This project uses MongoDB as its persistence layer. The easiest way to run MongoDB is using Docker.

## 1. Create an environment file

Create a `.env` file containing the MongoDB credentials.

```env
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=your-secure-password
```

> **Note:** Do not commit this file to version control. Add `.env` to your `.gitignore`.

---

## 2. Start MongoDB

From the directory containing your `.env` file, run:

```bash
docker run -d \
  --name mongodb \
  --restart unless-stopped \
  --env-file .env \
  -p 27017:27017 \
  -v mongodb_data:/data/db \
  mongo:latest
```

This command will:

* Start MongoDB in the background.
* Persist data in the `mongodb_data` Docker volume.
* Automatically restart MongoDB after a server reboot.
* Initialize the root user using the credentials from the `.env` file.

---

## 3. Verify MongoDB is running

Check the container status:

```bash
docker ps
```

You should see a running container named `mongodb`.

To view the logs:

```bash
docker logs -f mongodb
```

---

## 4. MongoDB Connection URI

Applications can connect to MongoDB using the following URI format:

```text
mongodb://<username>:<password>@<host>:<port>/?authSource=admin
```

For a local installation:

```text
mongodb://admin:your-secure-password@localhost:27017/?authSource=admin
```

If your application runs on a different machine, replace `localhost` with the hostname or IP address of the MongoDB server:

```text
mongodb://admin:your-secure-password@192.168.1.100:27017/?authSource=admin
```

---

## 5. Example Environment Variables

```env
AGENT_MONGO_URI=mongodb://admin:your-secure-password@localhost:27017/?authSource=admin
AGENT_MONGO_DB_NAME=langgraph
```

These values can then be used directly by the application configuration.

---

## 6. Useful Docker Commands

Check running containers:

```bash
docker ps
```

Stop MongoDB:

```bash
docker stop mongodb
```

Start MongoDB:

```bash
docker start mongodb
```

View logs:

```bash
docker logs -f mongodb
```

Remove the container (data is preserved in the Docker volume):

```bash
docker rm -f mongodb
```

Remove the persistent data volume:

```bash
docker volume rm mongodb_data
```

> **Warning:** Removing the Docker volume permanently deletes all MongoDB data.

Set max map count to higher value
```
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

Set swappiness = 1
```
echo "vm.swappiness=1" | sudo tee -a /etc/sysctl.conf
```