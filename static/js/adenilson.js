document.addEventListener("DOMContentLoaded", () => {
  const campoBusca = document.getElementById("buscaEmpresa");
  const filtroStatus = document.getElementById("filtroStatus");
  const botaoLimpar = document.getElementById("limparFiltros");
  const mensagemSemResultados = document.getElementById("mensagemSemResultados") || document.getElementById("semResultados");
  const contadorResultados = document.getElementById("quantidadeVisivel") || document.getElementById("contadorResultados");
  const totalEmpresas = document.getElementById("totalEmpresas");
  const corpoTabela = document.getElementById("corpoTabela");
  const linhasEmpresas = Array.from(document.querySelectorAll(".linha-empresa, .empresa-linha"));

  function normalizarTexto(texto) {
    return String(texto || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();
  }

  function obterDataLocal() {
    const hoje = new Date();
    const ano = hoje.getFullYear();
    const mes = String(hoje.getMonth() + 1).padStart(2, "0");
    const dia = String(hoje.getDate()).padStart(2, "0");

    return `${ano}-${mes}-${dia}`;
  }

  function formatarData(dataISO) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(dataISO)) {
      return dataISO || "Não informada";
    }

    const [ano, mes, dia] = dataISO.split("-");

    return `${dia}/${mes}/${ano}`;
  }

  function criarClasseStatus(status) {
    return "status-" + normalizarTexto(status)
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  }

  function prepararEmpresas() {
    const hoje = obterDataLocal();

    linhasEmpresas.forEach((linha) => {
      const status =
        linha.dataset.status ||
        "";

      const vencimento =
        linha.dataset.vencimento ||
        "";

      const badge = linha.querySelector(".status-badge");

      const elementoData = linha.querySelector(
        ".data-vencimento"
      );

      const elementoSituacao = linha.querySelector(
        ".situacao-vencimento"
      );

      // Aplica uma classe CSS específica para o status.
      if (badge) {
        badge.classList.add(criarClasseStatus(status));
      }

      // Formata o vencimento para DD/MM/AAAA.
      if (elementoData && vencimento) {
        elementoData.textContent = formatarData(vencimento);
      }

      // Destaca vencimentos passados e vencimentos de hoje.
      linha.classList.remove(
        "vencimento-atrasado",
        "vencimento-hoje"
      );

      if (vencimento && vencimento < hoje) {
        linha.classList.add("vencimento-atrasado");

        if (elementoSituacao) {
          elementoSituacao.textContent =
            "Vencimento ultrapassado";
        }
      } else if (vencimento === hoje) {
        linha.classList.add("vencimento-hoje");

        if (elementoSituacao) {
          elementoSituacao.textContent = "Vence hoje";
        }
      }
    });
  }

  // ==================================================
  // 4. FILTRO DE BUSCA E STATUS
  // ==================================================

  function filtrarEmpresas() {
    const termoBusca = normalizarTexto(
      campoBusca?.value || ""
    );

    const statusSelecionado =
      filtroStatus?.value || "";

    let quantidadeVisivel = 0;

    linhasEmpresas.forEach((linha) => {
      const nome = normalizarTexto(linha.dataset.nome || "");
      const cnpj = normalizarTexto(linha.dataset.cnpj || "");
      const tecnico = normalizarTexto(linha.dataset.tecnico || "");
      const unidade = normalizarTexto(linha.dataset.unidade || "");
      const buscaCompleta = normalizarTexto(linha.dataset.search || "");
      const status = linha.dataset.status || "";
      // Permite pesquisar por nome, CNPJ, técnico e unidade.
      const correspondeBusca =
        nome.includes(termoBusca) ||
        cnpj.includes(termoBusca) ||
        tecnico.includes(termoBusca) ||
        unidade.includes(termoBusca) ||
        buscaCompleta.includes(termoBusca);

      const correspondeStatus =
        statusSelecionado === "" ||
        status === statusSelecionado;

      const deveExibir =
        correspondeBusca && correspondeStatus;

      // Compatível com CSS que usa .hidden ou o atributo hidden.
      linha.classList.toggle("hidden", !deveExibir);
      linha.hidden = !deveExibir;

      if (deveExibir) {
        quantidadeVisivel++;
      }
    });

    // Atualiza o contador de resultados.
    if (contadorResultados) {
      contadorResultados.textContent =
        `Exibindo ${quantidadeVisivel} de ${linhasEmpresas.length} empresas`;
    }

    // Atualiza a mensagem de busca sem resultados.
    if (mensagemSemResultados) {
      mensagemSemResultados.classList.toggle(
        "hidden",
        quantidadeVisivel !== 0
      );

      mensagemSemResultados.hidden =
        quantidadeVisivel !== 0;
    }

    // O total do período não muda com os filtros.
    if (totalEmpresas) {
      totalEmpresas.textContent = linhasEmpresas.length;
    }
  }

  // ==================================================
  // 5. LIMPAR FILTROS
  // ==================================================

  function limparFiltros() {
    if (campoBusca) {
      campoBusca.value = "";
    }

    if (filtroStatus) {
      filtroStatus.value = "";
    }

    filtrarEmpresas();

    campoBusca?.focus();
  }

  // ==================================================
  // 6. CONFIRMAÇÃO DAS AÇÕES DE ADENILSON
  // ==================================================

  function configurarConfirmacoes() {
    const formularios = document.querySelectorAll(
      ".form-acao"
    );

    formularios.forEach((formulario) => {
      formulario.addEventListener("submit", (evento) => {
        const botao = formulario.querySelector(
          'button[type="submit"]'
        );

        const acao = botao
          ? botao.textContent.trim()
          : "executar esta ação";

        const confirmado = window.confirm(
          `Confirma a ação "${acao}" para esta empresa?`
        );

        if (!confirmado) {
          evento.preventDefault();
        }
      });
    });
  }

  // ==================================================
  // 7. EVENTOS
  // ==================================================

  campoBusca?.addEventListener(
    "input",
    filtrarEmpresas
  );

  filtroStatus?.addEventListener(
    "change",
    filtrarEmpresas
  );

  botaoLimpar?.addEventListener(
    "click",
    limparFiltros
  );

  // ==================================================
  // 8. INICIALIZAÇÃO
  // ==================================================

  prepararEmpresas();
  filtrarEmpresas();
  configurarConfirmacoes();

  console.log(
    "Painel do Adenilson carregado. " +
    `${linhasEmpresas.length} empresas encontradas na tabela.`
  );
});

// Botão Copiar

document.addEventListener("click", async (evento) => {
  const botao = evento.target.closest(".botao-copiar-cnpj");

  if (!botao) {
    return;
  }

  const cnpj = botao.dataset.cnpj;

  try {
    await navigator.clipboard.writeText(cnpj);

    const textoOriginal = botao.textContent;

    botao.textContent = "Copiado!";
    botao.classList.add("copiado");

    setTimeout(() => {
      botao.textContent = textoOriginal;
      botao.classList.remove("copiado");
    }, 1500);

  } catch (erro) {
    console.error("Erro ao copiar o CNPJ:", erro);
    alert("Não foi possível copiar o CNPJ.");
  }
});