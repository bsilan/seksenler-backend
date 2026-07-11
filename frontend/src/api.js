const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function req(method, path, body) {
  const res = await fetch(API + path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail || 'Bir şeyler ters gitti.');
    err.status = res.status;
    throw err;
  }
  return data;
}

export const createGame = (nickname) => req('POST', '/create_game', { nickname });
export const joinGame = (gameId, nickname) => req('POST', `/join_game/${gameId}`, { nickname });
export const startGame = (gameId) => req('POST', `/start_game/${gameId}`);
export const getState = (gameId, playerId) => req('GET', `/game_state/${gameId}/${playerId}`);
export const getMyRole = (gameId, playerId) => req('GET', `/my_role/${gameId}/${playerId}`);
export const nominate = (gameId, presidentId, nomineeNickname) =>
  req('POST', `/nominate/${gameId}`, { president_id: presidentId, nominee_nickname: nomineeNickname });
export const vote = (gameId, playerId, v) =>
  req('POST', `/vote/${gameId}`, { player_id: playerId, vote: v });
export const presidentDiscard = (gameId, presidentId, cardIndex) =>
  req('POST', `/president_discard/${gameId}`, { president_id: presidentId, card_index: cardIndex });
export const chancellorEnact = (gameId, chancellorId, cardIndex) =>
  req('POST', `/chancellor_enact/${gameId}`, { chancellor_id: chancellorId, card_index: cardIndex });
export const usePower = (gameId, presidentId, targetNickname) =>
  req('POST', `/use_power/${gameId}`, { president_id: presidentId, target_nickname: targetNickname });
export const proposeVeto = (gameId, chancellorId) =>
  req('POST', `/propose_veto/${gameId}`, { chancellor_id: chancellorId });
export const vetoDecision = (gameId, presidentId, approve) =>
  req('POST', `/veto_decision/${gameId}`, { president_id: presidentId, approve });
