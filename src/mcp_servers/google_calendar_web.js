#!/usr/bin/env node

/**
 * Google Calendar MCP Server - Web Application OAuth Flow
 * Supports multi-device deployment with proper OAuth callback handling
 */

import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { McpError, ErrorCode } from '@modelcontextprotocol/sdk/types.js';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { google } from 'googleapis';
import express from 'express';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import open from 'open';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class GoogleCalendarMCPServer {
    constructor() {
        this.server = new Server({
            name: 'google-calendar-web',
            version: '1.0.0',
            description: 'Google Calendar MCP Server with Web OAuth Flow'
        }, {
            capabilities: {
                tools: {}
            }
        });

        this.oauth2Client = null;
        this.calendar = null;
        this.authServer = null;
        this.authServerPort = process.env.GOOGLE_OAUTH_PORT || 3000;
        this.redirectUri = process.env.GOOGLE_REDIRECT_URI || `http://localhost:${this.authServerPort}/oauth2callback`;
        
        this.setupToolHandlers();
        this.initializeGoogleClient();
    }

    async initializeGoogleClient() {
        try {
            // Load OAuth credentials
            const credentialsPath = path.join(__dirname, '..', '..', 'gcp-oauth.keys.json');
            const credentialsContent = await fs.readFile(credentialsPath, 'utf8');
            const credentials = JSON.parse(credentialsContent);
            
            // Use web credentials
            const { client_id, client_secret } = credentials.web;
            
            this.oauth2Client = new google.auth.OAuth2(
                client_id,
                client_secret,
                this.redirectUri
            );

            // Try to load existing tokens
            await this.loadTokens();
            
            if (this.oauth2Client.credentials && this.oauth2Client.credentials.access_token) {
                this.calendar = google.calendar({ version: 'v3', auth: this.oauth2Client });
                console.error('✅ Google Calendar API initialized with existing tokens');
            } else {
                console.error('⚠️ No valid tokens found. Authentication required.');
            }

        } catch (error) {
            console.error('❌ Error initializing Google client:', error.message);
        }
    }

    async loadTokens() {
        try {
            const tokenPath = path.join(__dirname, '..', '..', 'google-tokens.json');
            const tokenContent = await fs.readFile(tokenPath, 'utf8');
            const tokens = JSON.parse(tokenContent);
            this.oauth2Client.setCredentials(tokens);
            console.error('✅ Loaded existing tokens');
        } catch (error) {
            console.error('⚠️ No existing tokens found');
        }
    }

    async saveTokens(tokens) {
        try {
            const tokenPath = path.join(__dirname, '..', '..', 'google-tokens.json');
            await fs.writeFile(tokenPath, JSON.stringify(tokens, null, 2));
            console.error('✅ Tokens saved successfully');
        } catch (error) {
            console.error('❌ Error saving tokens:', error.message);
        }
    }

    async authenticate() {
        return new Promise((resolve, reject) => {
            if (this.authServer) {
                console.error('⚠️ Authentication already in progress');
                resolve(false);
                return;
            }

            // Create Express server for OAuth callback
            const app = express();
            
            app.get('/oauth2callback', async (req, res) => {
                const { code, error } = req.query;
                
                if (error) {
                    res.send(`❌ Authentication failed: ${error}`);
                    this.authServer.close();
                    this.authServer = null;
                    reject(new Error(`Authentication failed: ${error}`));
                    return;
                }

                try {
                    const { tokens } = await this.oauth2Client.getToken(code);
                    this.oauth2Client.setCredentials(tokens);
                    await this.saveTokens(tokens);
                    
                    this.calendar = google.calendar({ version: 'v3', auth: this.oauth2Client });
                    
                    res.send(`
                        <html>
                            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                                <h2>✅ Authentication Successful!</h2>
                                <p>You can now close this tab and return to your application.</p>
                                <script>setTimeout(() => window.close(), 3000);</script>
                            </body>
                        </html>
                    `);
                    
                    console.error('✅ Authentication completed successfully');
                    
                    // Close server after successful auth
                    setTimeout(() => {
                        this.authServer.close();
                        this.authServer = null;
                    }, 1000);
                    
                    resolve(true);
                    
                } catch (authError) {
                    console.error('❌ Error during token exchange:', authError.message);
                    res.send(`❌ Error during authentication: ${authError.message}`);
                    this.authServer.close();
                    this.authServer = null;
                    reject(authError);
                }
            });

            // Start the server
            this.authServer = app.listen(this.authServerPort, () => {
                console.error(`🌐 OAuth callback server started on port ${this.authServerPort}`);
                
                // Generate auth URL
                const authUrl = this.oauth2Client.generateAuthUrl({
                    access_type: 'offline',
                    scope: [
                        'https://www.googleapis.com/auth/calendar',
                        'https://www.googleapis.com/auth/calendar.events'
                    ],
                    prompt: 'consent'
                });

                console.error('🔗 Please visit this URL to authenticate:');
                console.error(authUrl);
                
                // Try to open browser automatically
                open(authUrl).catch(() => {
                    console.error('⚠️ Could not open browser automatically. Please copy the URL above.');
                });
            });

            // Timeout after 5 minutes
            setTimeout(() => {
                if (this.authServer) {
                    console.error('⏰ Authentication timeout');
                    this.authServer.close();
                    this.authServer = null;
                    reject(new Error('Authentication timeout'));
                }
            }, 5 * 60 * 1000);
        });
    }

    async ensureAuthenticated() {
        if (!this.calendar || !this.oauth2Client.credentials) {
            console.error('🔐 Authentication required. Starting OAuth flow...');
            await this.authenticate();
        }
        
        // Check if token needs refresh
        if (this.oauth2Client.credentials.expiry_date && 
            this.oauth2Client.credentials.expiry_date <= Date.now()) {
            try {
                console.error('🔄 Refreshing expired token...');
                const { credentials } = await this.oauth2Client.refreshAccessToken();
                this.oauth2Client.setCredentials(credentials);
                await this.saveTokens(credentials);
                console.error('✅ Token refreshed successfully');
            } catch (error) {
                console.error('❌ Error refreshing token, re-authenticating...');
                await this.authenticate();
            }
        }
    }

    setupToolHandlers() {
        this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
            tools: [
                {
                    name: 'list_calendars',
                    description: 'List all available calendars',
                    inputSchema: {
                        type: 'object',
                        properties: {},
                        required: []
                    }
                },
                {
                    name: 'list_events',
                    description: 'List events from a calendar',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            calendarId: {
                                type: 'string',
                                description: 'Calendar ID (default: primary)',
                                default: 'primary'
                            },
                            maxResults: {
                                type: 'number',
                                description: 'Maximum number of events to return',
                                default: 10
                            },
                            timeMin: {
                                type: 'string',
                                description: 'Lower bound for events (ISO 8601)'
                            },
                            timeMax: {
                                type: 'string',
                                description: 'Upper bound for events (ISO 8601)'
                            }
                        },
                        required: []
                    }
                },
                {
                    name: 'create_event',
                    description: 'Create a new calendar event',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            calendarId: {
                                type: 'string',
                                description: 'Calendar ID (default: primary)',
                                default: 'primary'
                            },
                            summary: {
                                type: 'string',
                                description: 'Event title'
                            },
                            description: {
                                type: 'string',
                                description: 'Event description'
                            },
                            startDateTime: {
                                type: 'string',
                                description: 'Start date/time (ISO 8601)'
                            },
                            endDateTime: {
                                type: 'string',
                                description: 'End date/time (ISO 8601)'
                            },
                            location: {
                                type: 'string',
                                description: 'Event location'
                            }
                        },
                        required: ['summary', 'startDateTime', 'endDateTime']
                    }
                },
                {
                    name: 'get_upcoming_events',
                    description: 'Get upcoming events for the next specified days',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            days: {
                                type: 'number',
                                description: 'Number of days to look ahead',
                                default: 7
                            },
                            calendarId: {
                                type: 'string',
                                description: 'Calendar ID (default: primary)',
                                default: 'primary'
                            }
                        },
                        required: []
                    }
                }
            ]
        }));

        this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
            await this.ensureAuthenticated();
            
            switch (request.params.name) {
                case 'list_calendars':
                    return await this.listCalendars();
                case 'list_events':
                    return await this.listEvents(request.params.arguments);
                case 'create_event':
                    return await this.createEvent(request.params.arguments);
                case 'get_upcoming_events':
                    return await this.getUpcomingEvents(request.params.arguments);
                default:
                    throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${request.params.name}`);
            }
        });
    }

    async listCalendars() {
        try {
            const response = await this.calendar.calendarList.list();
            const calendars = response.data.items.map(cal => ({
                id: cal.id,
                summary: cal.summary,
                primary: cal.primary,
                accessRole: cal.accessRole,
                backgroundColor: cal.backgroundColor
            }));

            return {
                content: [{
                    type: 'text',
                    text: `Found ${calendars.length} calendars:\n${calendars.map(cal => 
                        `• ${cal.summary} (${cal.id})${cal.primary ? ' [PRIMARY]' : ''}`
                    ).join('\n')}`
                }]
            };
        } catch (error) {
            throw new McpError(ErrorCode.InternalError, `Failed to list calendars: ${error.message}`);
        }
    }

    async listEvents(args = {}) {
        try {
            const calendarId = args.calendarId || 'primary';
            const maxResults = args.maxResults || 10;
            
            const params = {
                calendarId,
                maxResults,
                singleEvents: true,
                orderBy: 'startTime'
            };
            
            if (args.timeMin) params.timeMin = args.timeMin;
            if (args.timeMax) params.timeMax = args.timeMax;
            
            const response = await this.calendar.events.list(params);
            const events = response.data.items || [];
            
            if (events.length === 0) {
                return {
                    content: [{
                        type: 'text',
                        text: 'No events found.'
                    }]
                };
            }
            
            const eventList = events.map(event => {
                const start = event.start.dateTime || event.start.date;
                const end = event.end.dateTime || event.end.date;
                return `• ${event.summary} (${start} - ${end})${event.location ? ` @ ${event.location}` : ''}`;
            }).join('\n');
            
            return {
                content: [{
                    type: 'text',
                    text: `Found ${events.length} events:\n${eventList}`
                }]
            };
        } catch (error) {
            throw new McpError(ErrorCode.InternalError, `Failed to list events: ${error.message}`);
        }
    }

    async createEvent(args) {
        try {
            const calendarId = args.calendarId || 'primary';
            
            const event = {
                summary: args.summary,
                description: args.description,
                location: args.location,
                start: {
                    dateTime: args.startDateTime,
                    timeZone: 'America/Argentina/Buenos_Aires'
                },
                end: {
                    dateTime: args.endDateTime,
                    timeZone: 'America/Argentina/Buenos_Aires'
                }
            };
            
            const response = await this.calendar.events.insert({
                calendarId,
                resource: event
            });
            
            return {
                content: [{
                    type: 'text',
                    text: `✅ Event created successfully: "${response.data.summary}" on ${response.data.start.dateTime}\nEvent ID: ${response.data.id}\nHTML Link: ${response.data.htmlLink}`
                }]
            };
        } catch (error) {
            throw new McpError(ErrorCode.InternalError, `Failed to create event: ${error.message}`);
        }
    }

    async getUpcomingEvents(args = {}) {
        try {
            const days = args.days || 7;
            const calendarId = args.calendarId || 'primary';
            
            const now = new Date();
            const future = new Date();
            future.setDate(now.getDate() + days);
            
            return await this.listEvents({
                calendarId,
                timeMin: now.toISOString(),
                timeMax: future.toISOString(),
                maxResults: 50
            });
        } catch (error) {
            throw new McpError(ErrorCode.InternalError, `Failed to get upcoming events: ${error.message}`);
        }
    }

    async run() {
        const transport = new StdioServerTransport();
        await this.server.connect(transport);
        console.error('🚀 Google Calendar MCP Server (Web OAuth) running');
    }
}

// Start the server
const server = new GoogleCalendarMCPServer();
server.run().catch(console.error);