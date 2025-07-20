-- Jarvis Multi-Agent AI System Database Schema
-- PostgreSQL with pgvector extension

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create custom types
CREATE TYPE message_type AS ENUM ('user', 'agent', 'system', 'tool');
CREATE TYPE agent_status AS ENUM ('active', 'idle', 'error', 'maintenance');
CREATE TYPE tool_status AS ENUM ('available', 'installing', 'error', 'deprecated');
CREATE TYPE session_status AS ENUM ('active', 'paused', 'completed', 'error');

-- Sessions table for tracking user conversations
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255),
    status session_status DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    total_cost DECIMAL(10, 4) DEFAULT 0.00,
    total_tokens INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Chat logs for conversation history
CREATE TABLE chat_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    agent_id VARCHAR(100),
    message_type message_type NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    tokens_used INTEGER DEFAULT 0,
    cost DECIMAL(8, 4) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Vector embedding for semantic search
    embedding vector(1536)
);

-- Agents registry
CREATE TABLE agents (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    model_name VARCHAR(100) NOT NULL,
    model_provider VARCHAR(50) NOT NULL,
    status agent_status DEFAULT 'idle',
    system_message TEXT,
    config JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE
);

-- Tool registry for MCP management
CREATE TABLE tool_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tool_name VARCHAR(255) NOT NULL UNIQUE,
    tool_version VARCHAR(50) NOT NULL,
    description TEXT,
    status tool_status DEFAULT 'available',
    install_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    config JSONB DEFAULT '{}'::jsonb,
    safety_score INTEGER CHECK (safety_score >= 0 AND safety_score <= 100),
    usage_count INTEGER DEFAULT 0,
    last_used TIMESTAMP WITH TIME ZONE
);

-- Cost tracking for LLM usage
CREATE TABLE cost_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    agent_id VARCHAR(100) REFERENCES agents(id),
    model_name VARCHAR(100) NOT NULL,
    operation_type VARCHAR(50) NOT NULL, -- 'completion', 'embedding', 'tool_call'
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    tokens_total INTEGER GENERATED ALWAYS AS (tokens_input + tokens_output) STORED,
    cost DECIMAL(8, 4) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- File index for RAG documents
CREATE TABLE file_index (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_hash VARCHAR(64) NOT NULL UNIQUE,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_date TIMESTAMP WITH TIME ZONE,
    chunk_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Full-text search
    content_tsvector tsvector
);

-- Document chunks for RAG
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id UUID NOT NULL REFERENCES file_index(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Vector embedding for semantic search
    embedding vector(1536),
    
    UNIQUE(file_id, chunk_index)
);

-- Reflexion logs for self-improvement
CREATE TABLE reflexion_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    task_id UUID,
    task_description TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    analysis TEXT,
    heuristics JSONB DEFAULT '[]'::jsonb,
    improvement_suggestions TEXT,
    confidence_score DECIMAL(3, 2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Voice processing logs
CREATE TABLE voice_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    operation_type VARCHAR(20) NOT NULL, -- 'stt', 'tts'
    provider VARCHAR(50) NOT NULL,
    input_format VARCHAR(20),
    output_format VARCHAR(20),
    duration_ms INTEGER,
    processing_time_ms INTEGER,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- System metrics for monitoring
CREATE TABLE system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(12, 4) NOT NULL,
    metric_unit VARCHAR(20),
    component VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for performance
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_created_at ON sessions(created_at);

CREATE INDEX idx_chat_logs_session_id ON chat_logs(session_id);
CREATE INDEX idx_chat_logs_agent_id ON chat_logs(agent_id);
CREATE INDEX idx_chat_logs_message_type ON chat_logs(message_type);
CREATE INDEX idx_chat_logs_created_at ON chat_logs(created_at);
CREATE INDEX idx_chat_logs_embedding ON chat_logs USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_model_provider ON agents(model_provider);
CREATE INDEX idx_agents_last_activity ON agents(last_activity);

CREATE INDEX idx_tool_registry_status ON tool_registry(status);
CREATE INDEX idx_tool_registry_tool_name ON tool_registry(tool_name);
CREATE INDEX idx_tool_registry_usage_count ON tool_registry(usage_count);

CREATE INDEX idx_cost_history_session_id ON cost_history(session_id);
CREATE INDEX idx_cost_history_agent_id ON cost_history(agent_id);
CREATE INDEX idx_cost_history_created_at ON cost_history(created_at);
CREATE INDEX idx_cost_history_model_name ON cost_history(model_name);

CREATE INDEX idx_file_index_file_hash ON file_index(file_hash);
CREATE INDEX idx_file_index_upload_date ON file_index(upload_date);
CREATE INDEX idx_file_index_content_tsvector ON file_index USING gin(content_tsvector);

CREATE INDEX idx_document_chunks_file_id ON document_chunks(file_id);
CREATE INDEX idx_document_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX idx_reflexion_log_session_id ON reflexion_log(session_id);
CREATE INDEX idx_reflexion_log_success ON reflexion_log(success);
CREATE INDEX idx_reflexion_log_created_at ON reflexion_log(created_at);

CREATE INDEX idx_voice_logs_session_id ON voice_logs(session_id);
CREATE INDEX idx_voice_logs_operation_type ON voice_logs(operation_type);
CREATE INDEX idx_voice_logs_success ON voice_logs(success);

CREATE INDEX idx_system_metrics_metric_name ON system_metrics(metric_name);
CREATE INDEX idx_system_metrics_component ON system_metrics(component);
CREATE INDEX idx_system_metrics_created_at ON system_metrics(created_at);

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default agents
INSERT INTO agents (id, name, description, model_name, model_provider, system_message) VALUES
('agent1_openrouter_gpt40', 'GPT-4o Agent', 'Primary reasoning agent using GPT-4o', 'gpt-4o', 'openrouter', 'You are a helpful AI assistant with advanced reasoning capabilities.'),
('agent2_ollama_gemma3_7b', 'Gemma3 Agent', 'Local agent using Gemma3 7B model', 'gemma2:7b', 'ollama', 'You are a knowledgeable AI assistant running locally.'),
('agent3_openrouter_gemini25', 'Gemini Agent', 'Google Gemini 2.5 Flash agent', 'gemini-2.5-flash', 'openrouter', 'You are an AI assistant powered by Google Gemini with multimodal capabilities.'),
('agent4_ollama_llama4_32b', 'Llama Agent', 'Local agent using Llama 3.2 8B model', 'llama3.2:8b', 'ollama', 'You are a capable AI assistant based on the Llama architecture.');

-- Create views for common queries
CREATE VIEW session_summary AS
SELECT 
    s.id,
    s.user_id,
    s.status,
    s.created_at,
    s.total_cost,
    s.total_tokens,
    COUNT(cl.id) as message_count,
    COUNT(DISTINCT cl.agent_id) as agents_used
FROM sessions s
LEFT JOIN chat_logs cl ON s.id = cl.session_id
GROUP BY s.id, s.user_id, s.status, s.created_at, s.total_cost, s.total_tokens;

CREATE VIEW agent_performance AS
SELECT 
    a.id,
    a.name,
    a.model_name,
    a.status,
    COUNT(cl.id) as total_messages,
    SUM(cl.tokens_used) as total_tokens,
    SUM(cl.cost) as total_cost,
    AVG(cl.cost) as avg_cost_per_message,
    MAX(cl.created_at) as last_used
FROM agents a
LEFT JOIN chat_logs cl ON a.id = cl.agent_id
GROUP BY a.id, a.name, a.model_name, a.status;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO jarvis_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO jarvis_user;
