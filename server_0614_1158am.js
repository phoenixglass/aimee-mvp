const express = require('express');
const cors = require('cors');
const fetch = require('node-fetch'); // required for OpenAI + ElevenLabs

const app = express(); // define the app before using it
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

app.post('/api/voice-query', async (req, res) => {
  const { query, isIOS } = req.body;
  console.log('Voice query received:', query);

  if (!query) {
    return res.status(400).json({ error: 'Query missing' });
  }

  const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
  const ELEVENLABS_API_KEY = process.env.ELEVENLABS_API_KEY;
  const VOICE_ID = process.env.VOICE_ID || 'rzsnuMd2pwYz1rGtMIVI';
  console.log('Using ElevenLabs voice ID:', VOICE_ID);

  // 🧠 Get GPT response
  let response = 'Sorry, I could not process that.';
  try {
    const aiRes = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENAI_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'gpt-4', // or 'gpt-3.5-turbo'
        messages: [
          { role: 'system', content: 'You are Aimee, a voice-powered wine sales assistant. Answer clearly and concisely.' },
          { role: 'user', content: query }
        ],
        temperature: 0.6
      })
    });

    const data = await aiRes.json();
    response = data.choices?.[0]?.message?.content?.trim() || response;
  } catch (err) {
    console.error('OpenAI error:', err.message);
  }

  // 🖙️ ElevenLabs TTS
  let audioUrl = null;
  if (ELEVENLABS_API_KEY && !isIOS) {
    try {
      console.log('↓ Requesting voice with ID:', VOICE_ID);
      console.log('Base64 audio preview:', base64Audio.slice(0, 80) + '...');

      const audioResponse = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}`, {
        method: 'POST',
        headers: {
          'Accept': 'audio/mpeg',
          'Content-Type': 'application/json',
          'xi-api-key': ELEVENLABS_API_KEY
        },
        body: JSON.stringify({
          text: response,
          model_id: 'eleven_monolingual_v1',
          voice_settings: {
            stability: 0.5,
            similarity_boost: 0.5
          }
        })
      });

      if (audioResponse.ok) {
        const audioBuffer = await audioResponse.arrayBuffer();
        const base64Audio = Buffer.from(audioBuffer).toString('base64');
        audioUrl = `data:audio/mpeg;base64,${base64Audio}`;
        console.log('✅ ElevenLabs TTS response OK');
      }
    } catch (error) {
      console.error('ElevenLabs TTS error:', error.message);
    }
  }

  res.json({ response, audioUrl });
});

app.listen(PORT, () => {
  console.log(`Aimee backend running at http://localhost:${PORT}`);
});