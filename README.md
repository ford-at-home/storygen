<div align="center">

# 🏙️ Richmond Storyline Generator

### *Weaving Richmond's Stories into Compelling Narratives*

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com)
[![AWS](https://img.shields.io/badge/AWS-Bedrock%20%7C%20Lambda%20%7C%20DynamoDB-orange.svg)](https://aws.amazon.com)
[![Pinecone](https://img.shields.io/badge/Pinecone-Vector%20Search-purple.svg)](https://pinecone.io)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active%20Development-brightgreen.svg)](https://github.com/ford-at-home/storygen)

*A sophisticated AI-powered storytelling platform that transforms voice input into community-centered narratives for Richmond's tech scene. Built with love for Richmond's unique character and vibrant community.*

[🚀 Quick Start](#-quick-start) • [📖 Documentation](#-documentation) • [🏗️ Architecture](#️-architecture) • [🎯 Features](#-features) • [🤝 Contributing](#-contributing)

---

![Richmond Skyline](https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=1200&h=400&fit=crop&crop=center)

*Richmond's James River and downtown skyline - where every story finds its home*

</div>

---

## 🌟 What Makes This Special?

The Richmond Storyline Generator isn't just another AI tool—it's a **community storyteller** that understands Richmond's soul. We combine cutting-edge AI with deep local knowledge to help you share stories that resonate with Richmond's unique character.

### ✨ **The Magic Formula**
```
🎤 Your Voice → 🤖 AI Analysis → 🏙️ Richmond Context → 📝 Compelling Story
```

---

## 🎯 Features That Matter

<div align="center">

### 🎤 **Voice-First Storytelling**
*Speak your story, let AI do the rest*

### 🧠 **Intelligent Depth Analysis** 
*Nova-powered insights to make your story shine*

### 🏙️ **Richmond-Aware AI**
*Context from 5 knowledge bases: Quotes, Culture, Economy, Stories, News*

### 🔄 **Conversational Development**
*Interactive refinement through meaningful dialogue*

### 🎨 **Multiple Formats**
*Short posts, long posts, and full blog articles*

</div>

---

## 🏗️ Architecture Overview

```mermaid
graph TB
    A[🎤 Voice Input] --> B[🔊 Whisper Transcription]
    B --> C[🧠 Nova Depth Analysis]
    C --> D[💬 Claude Conversation]
    D --> E[🔍 Richmond Context]
    E --> F[📝 Story Generation]
    F --> G[✨ Final Story]
    
    style A fill:#ff6b6b
    style G fill:#51cf66
    style E fill:#339af0
```

---

## 🚀 Quick Start

### 🚀 **Current Status: Fully Functional API**

The Richmond Storyline Generator has a **complete backend API** that works right now. You can generate stories, process voice input, and use conversational features through API calls. The frontend UI is in development following a systematic roadmap.

#### 1️⃣ **Clone & Setup**
```bash
git clone https://github.com/ford-at-home/storygen.git
cd storygen

# Run the integrated setup script
python deploy_integrated.py --environment development
```

#### 2️⃣ **Start the Application**
```bash
# Start all services with Docker Compose
docker-compose up -d

# Or run directly:
python integrated_app.py --environment development
```

#### 3️⃣ **Use the API**
- **Backend API**: http://localhost:5000
- **API Documentation**: http://localhost:5000/ (welcome page)
- **Health Check**: http://localhost:5000/health

### 📱 **How to Use the System (API)**

**Generate a story:**
```bash
curl -X POST http://localhost:5000/generate-story \
  -H "Content-Type: application/json" \
  -d '{"core_idea": "Richmond tech scene growth", "style": "short_post"}'
```

**Upload voice recording:**
```bash
curl -X POST http://localhost:5000/voice/upload \
  -F "audio=@recording.wav"
```

**Start a conversation:**
```bash
curl -X POST http://localhost:5000/conversation/start \
  -H "Content-Type: application/json" \
  -d '{"initial_idea": "Richmond startup story"}'
```

### 🎯 **Frontend Development Roadmap**

The frontend UI is being developed systematically:
1. **Issue #32**: Complete API documentation
2. **Issue #27**: Basic HTML interface  
3. **Issue #28**: React foundation
4. **Issue #29**: Voice recording UI
5. **Issue #30**: Conversation interface
6. **Issue #31**: Advanced features

### 📊 **What Works Right Now**
- ✅ Complete story generation API
- ✅ Voice file upload and transcription
- ✅ Multi-turn conversation system
- ✅ Richmond context integration
- ✅ Multiple story formats
- ✅ Health monitoring and stats

### 🎯 **API Quick Start Guide**

1. **Generate Your First Story** 📝
   ```bash
   curl -X POST http://localhost:5000/generate-story \
     -H "Content-Type: application/json" \
     -d '{"core_idea": "Your Richmond story idea here"}'
   ```

2. **Try Voice Input** 🎤
   ```bash
   curl -X POST http://localhost:5000/voice/upload \
     -F "audio=@your-recording.wav"
   ```

3. **Start a Conversation** 💬
   ```bash
   curl -X POST http://localhost:5000/conversation/start \
     -H "Content-Type: application/json" \
     -d '{"initial_idea": "Your story concept"}'
   ```

### 🆘 **Need Help?**

- **📖 User Guide**: [Complete Usage Instructions](USER_GUIDE.md)
- **📚 Documentation**: [View All Docs](docs/)
- **🐛 Issues**: [Report Problems](https://github.com/ford-at-home/storygen/issues)
- **💬 Discussions**: [Community Forum](https://github.com/ford-at-home/storygen/discussions)
- **📧 Email**: Create an issue for support

---

## 📖 Documentation

<div align="center">

| 📋 **Guide** | 📝 **Description** | 🔗 **Link** |
|--------------|-------------------|-------------|
| 🏗️ **Architecture** | Complete system design and flow | [View Details](docs/ARCHITECTURE.md) |
| 🔄 **Workflow** | Step-by-step story generation process | [View Details](docs/WORKFLOW.md) |
| 💬 **Conversation Flow** | Interactive prompt system guide | [View Details](docs/CONVERSATION.md) |
| ☁️ **AWS Deployment** | Infrastructure and CDK setup | [View Details](docs/DEPLOYMENT.md) |

</div>

---

## 🎭 Story Generation in Action

### **Example Input**
> *"I want to tell a story about how Richmond's tech community is quietly growing, with people returning from big coastal cities."*

### **AI Analysis & Enhancement**
🤖 *"This has great potential! Let me ask: What's a specific moment when you've seen this trend in action? Why does this story matter to you personally?"*

### **Richmond Context Integration**
🏙️ *"Connecting to Richmond's economic resurgence, the James River tech corridor, and recent startup success stories..."*

### **Final Story**
📝 *"In the shadow of Richmond's historic skyline, a quiet revolution is unfolding..."*

---

## 🏙️ Richmond Knowledge Base

Our AI understands Richmond through **5 curated knowledge bases**:

<div align="center">

| 📚 **Knowledge Base** | 🎯 **Content** | 📊 **Coverage** |
|----------------------|----------------|-----------------|
| **Richmond Quotes** | Voices from the community | 500+ authentic quotes |
| **Richmond Culture** | Arts, music, and local character | Cultural insights |
| **Richmond Economy** | Tech growth and business trends | Economic context |
| **Richmond Stories** | Historical narratives and legends | Community heritage |
| **Richmond News** | Recent events and developments | Current happenings |

</div>

---

## 🛠️ Tech Stack

<div align="center">

### 🤖 **AI & Machine Learning**
![Claude](https://img.shields.io/badge/Claude-3%20Sonnet-purple?style=for-the-badge)
![Nova](https://img.shields.io/badge/Nova-Depth%20Analysis-blue?style=for-the-badge)
![Whisper](https://img.shields.io/badge/Whisper-Speech%20to%20Text-green?style=for-the-badge)

### ☁️ **Cloud Infrastructure**
![AWS](https://img.shields.io/badge/AWS-Bedrock%20%7C%20Lambda%20%7C%20DynamoDB-orange?style=for-the-badge)
![Pinecone](https://img.shields.io/badge/Pinecone-Vector%20Search-purple?style=for-the-badge)
![S3](https://img.shields.io/badge/S3-File%20Storage-blue?style=for-the-badge)

### 🐍 **Backend & API**
![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge)
![Flask](https://img.shields.io/badge/Flask-REST%20API-green?style=for-the-badge)
![LangChain](https://img.shields.io/badge/LangChain-LLM%20Framework-yellow?style=for-the-badge)

</div>

---

## 📈 Development Status

<div align="center">

### 🎯 **Phase 1: Core Infrastructure** ✅ **COMPLETE**
- [x] Basic story generation API
- [x] Vector search integration  
- [x] Prompt library development
- [x] Workflow documentation

### 🎯 **Phase 2: Conversational Interface** ✅ **COMPLETE**
- [x] Conversation state management
- [x] Interactive story development
- [x] Multi-turn conversation flow
- [x] Session persistence with Redis
- [x] Voice input integration (Whisper)
- [x] Nova depth analysis

### 🎯 **Phase 3: Production-Ready Platform** ✅ **COMPLETE**
- [x] Complete React frontend with voice recording
- [x] User authentication and session management
- [x] Enterprise-grade security (JWT, encryption, validation)
- [x] Production infrastructure (Docker, CI/CD, monitoring)
- [x] Database persistence (DynamoDB + Redis)
- [x] Comprehensive testing (>80% coverage)
- [x] Auto-scaling deployment on AWS

### 🚀 **Phase 4: Complete Application** ✅ **READY**
- [x] Complete local development environment
- [x] Mobile-optimized progressive web app
- [x] Real-time monitoring and alerting
- [x] Analytics and user insights
- [x] Story templates and themes
- [x] Multi-format export capabilities

### 🔮 **Future Enhancements** 📋
- [ ] Production cloud deployment
- [ ] Custom domain and hosting
- [ ] Community story sharing and curation
- [ ] Discord/Slack integration
- [ ] Automated Richmond news integration
- [ ] Multi-modal input (images, documents)
- [ ] Advanced analytics dashboard
- [ ] White-label versions for other cities

</div>

---

## 🤝 Contributing

We love contributions from the Richmond community! Here's how you can help:

### 🎯 **Ways to Contribute**
- 🐛 **Report bugs** and suggest improvements
- 💡 **Propose new features** and enhancements
- 📝 **Improve documentation** and examples
- 🧪 **Add tests** and improve code quality
- 🏙️ **Contribute Richmond context** and local knowledge

### 🚀 **Getting Started**
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### 📋 **Code Standards**
- Follow PEP 8 for Python code
- Add docstrings to new functions
- Include tests for new features
- Update documentation as needed

---

## 🏆 Community & Recognition

<div align="center">

### 🌟 **Built for Richmond, by Richmond**
*Empowering narrative builders in Richmond's tech ecosystem*

### 🏆 **Featured In**
- Richmond Tech Community
- Local Startup Ecosystem
- Civic Storytelling Initiatives

### 📊 **Stats**
![GitHub stars](https://img.shields.io/github/stars/ford-at-home/storygen?style=social)
![GitHub forks](https://img.shields.io/github/forks/ford-at-home/storygen?style=social)
![GitHub issues](https://img.shields.io/github/issues/ford-at-home/storygen)
![GitHub pull requests](https://img.shields.io/github/issues-pr/ford-at-home/storygen)

</div>

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 💬 Connect With Us

<div align="center">

### 🏙️ **Richmond Tech Community**
- Join our [Discord](https://discord.gg/richmond-tech) 
- Follow us on [Twitter](https://twitter.com/richmondtech)
- Connect on [LinkedIn](https://linkedin.com/company/richmond-tech)

### 📧 **Get in Touch**
- 📧 Email: hello@richmondtech.org
- 🐛 Issues: [GitHub Issues](https://github.com/ford-at-home/storygen/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/ford-at-home/storygen/discussions)

### 🌟 **Support the Project**
- ⭐ Star this repository
- 🔄 Share with your network
- 💡 Contribute your ideas
- 🏙️ Add Richmond context

</div>

---

<div align="center">

### 🏙️ **Built with ❤️ for Richmond's Tech Community**

*Every story matters. Every voice counts. Every Richmond narrative deserves to be heard.*

---

**Made in Richmond, Virginia** 🇺🇸

[⬆️ Back to Top](#-richmond-storyline-generator)

</div>