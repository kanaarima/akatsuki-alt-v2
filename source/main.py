from back.taskmanager import TaskManager
import back.tasks.clan_tasks as clan_tasks
import back.tasks.user_tasks as user_tasks
import api.logging as logging
import front.bot as bot
import config
import sys


def wrong_args():
    print(f"Usage: {sys.argv[0]} backend/frontend")
    sys.exit(-1)


def main():
    if len(sys.argv) < 2:
        wrong_args()
    if sys.argv[1] == "frontend":
        logging.init("frontend")
        bot.main()
    elif sys.argv[1] == "backend":
        logging.init("backend")
        manager = TaskManager(
            [
                clan_tasks.StoreClanLeaderboardsTask(),
                user_tasks.StoreUserLeaderboardsTask(),
                user_tasks.StorePlayerStats(),
                user_tasks.StorePlayerScores(),
                user_tasks.TrackUserPlaytime(),
            ]
        )
        manager.loop()
    else:
        wrong_args()


if __name__ == "__main__":
    main()
