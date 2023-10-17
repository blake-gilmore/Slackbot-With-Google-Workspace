# Google Workspace SlackBot

This project showcases a SlackBot I created for streamlining the onboarding process within my organization. The SlackBot connects to our Google Cloud Platform project and Google Workspace to interact with user information and file information. It primarily focuses on the onboarding of interns.

## Features

- **Request Validation:** Before performing any functinos, the application will verify each incoming Slack request using Slack's X-Slack_Signature and compares to a SHA-256 hash created through the application using the applications global secret.

- **Onboarding Interns:** The main functionality of this SlackBot is to simplify the onboarding of interns. As an admin, I can call the bot through Slack using the command '/onboard-interns'.

- **CSV Data Input:** The bot will prompt me for a .csv file with a specific format containing intern names and contact information.

- **Google Workspace Group Assignment:** I can specify which Google Workspace groups the bot should place each new intern into.

- **Account Creation:** The SlackBot automatically creates Google Workspace accounts for incoming interns with strong passwords.

- **Email Notifications:** It sends welcome emails to the incoming interns.

- **Spreadsheet Population:** The bot populates a generic Intern Timesheet spreadsheet.

- **Folder Creation:** It creates individual folders for each intern.

## Usage

This project serves as a demonstration of what I've built, this project is not intended for general use or contributions.
